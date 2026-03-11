import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess
import requests


GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
GITHUB_API_URL = "https://api.github.com"


@dataclass
class RepositoryInfo:
    owner: str
    repo: str
    url: str
    clone_url: str
    default_branch: str
    is_private: bool


class GitHubCloneError(Exception):
    pass


class GitHubRepository:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get(GITHUB_TOKEN_ENV)
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"

    def parse_repo_url(self, repo_input: str) -> tuple[str, str]:
        repo_input = repo_input.strip().rstrip("/")
        
        if repo_input.startswith("https://github.com/"):
            match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", repo_input)
            if not match:
                raise GitHubCloneError(f"Invalid GitHub URL: {repo_input}")
            return match.group(1), match.group(2)
        
        if "/" in repo_input:
            parts = repo_input.split("/")
            if len(parts) != 2:
                raise GitHubCloneError(
                    f"Invalid repo format: {repo_input}. Expected org/repo or full GitHub URL"
                )
            return parts[0], parts[1]
        
        raise GitHubCloneError(
            f"Invalid repository: {repo_input}. Expected GitHub URL (https://github.com/owner/repo) or owner/repo format"
        )

    def get_repo_info(self, owner: str, repo: str) -> RepositoryInfo:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        response = self.session.get(url)
        
        if response.status_code == 404:
            raise GitHubCloneError(f"Repository not found: {owner}/{repo}")
        if response.status_code == 403 and not self.token:
            raise GitHubCloneError(
                f"Private repository {owner}/{repo} requires authentication. "
                f"Set {GITHUB_TOKEN_ENV} environment variable."
            )
        if response.status_code != 200:
            raise GitHubCloneError(
                f"GitHub API error: {response.status_code} - {response.text}"
            )
        
        data = response.json()
        
        return RepositoryInfo(
            owner=owner,
            repo=repo,
            url=data["html_url"],
            clone_url=data["clone_url"],
            default_branch=data.get("default_branch", "main"),
            is_private=data.get("private", False)
        )

    def clone(
        self,
        repo_input: str,
        target_dir: Optional[Path] = None,
        branch: Optional[str] = None,
        depth: int = 1
    ) -> tuple[Path, RepositoryInfo]:
        owner, repo = self.parse_repo_url(repo_input)
        
        repo_info = self.get_repo_info(owner, repo)
        
        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp(prefix="code_review_"))
        
        target_path = target_dir / repo
        if target_path.exists():
            shutil.rmtree(target_path)
        
        clone_url = repo_info.clone_url
        if self.token:
            clone_url = clone_url.replace(
                "https://", f"https://oauth2:{self.token}@"
            )
        
        cmd = ["git", "clone"]
        if depth:
            cmd.extend(["--depth", str(depth)])
        if branch:
            cmd.extend(["--branch", branch])
        else:
            cmd.extend(["--branch", repo_info.default_branch])
        cmd.extend([clone_url, str(target_path)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise GitHubCloneError(f"Git clone failed: {e.stderr}") from e
        
        return target_path, repo_info

    def fetch_contents(
        self,
        repo_input: str,
        path: str = "",
        ref: Optional[str] = None
    ) -> dict:
        owner, repo = self.parse_repo_url(repo_input)
        
        if ref is None:
            repo_info = self.get_repo_info(owner, repo)
            ref = repo_info.default_branch
        
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 404:
            raise GitHubCloneError(f"Path not found: {path} in {owner}/{repo}")
        if response.status_code != 200:
            raise GitHubCloneError(
                f"GitHub API error: {response.status_code} - {response.text}"
            )
        
        return response.json()

    def get_commit_hash(self, repo_path: Path, ref: Optional[str] = None) -> str:
        cmd = ["git", "rev-parse"]
        if ref:
            cmd.append(ref)
        else:
            cmd.append("HEAD")
        
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        return result.stdout.strip()

    def get_default_branch(self, repo_input: str) -> str:
        owner, repo = self.parse_repo_url(repo_input)
        repo_info = self.get_repo_info(owner, repo)
        return repo_info.default_branch


def clone_repository(
    repo_input: str,
    target_dir: Optional[Path] = None,
    branch: Optional[str] = None,
    token: Optional[str] = None
) -> tuple[Path, str, str]:
    github = GitHubRepository(token=token)
    repo_path, repo_info = github.clone(repo_input, target_dir, branch)
    commit_hash = github.get_commit_hash(repo_path)
    
    return repo_path, commit_hash, repo_info.default_branch
