import subprocess
from pathlib import Path
from typing import Optional


class CommitHashExtractor:
    """Extract commit hashes from git repositories.
    
    Supports three modes:
    - Specific commit: Returns the exact commit if it exists
    - Branch name: Returns the latest commit of the specified branch
    - Default: Returns the HEAD commit of the default branch
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")
    
    def _run_git(self, *args: str) -> str:
        """Run a git command and return the output."""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path)] + list(args),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def get_default_branch(self) -> str:
        """Get the default branch name of the repository."""
        remote_url = self._run_git("remote", "get-url", "origin")
        if "github.com" in remote_url.lower():
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "ls-remote", "--symref", "origin", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            for line in output.split("\n"):
                if "refs/heads/" in line:
                    return line.split("refs/heads/")[1].strip()
        return self._run_git("rev-parse", "--abbrev-ref", "HEAD")
    
    def get_commit_hash(self, ref: Optional[str] = None) -> str:
        """Get commit hash from a reference.
        
        Args:
            ref: Can be a specific commit hash, branch name, or None for default branch
            
        Returns:
            Full commit hash (40 characters)
            
        Raises:
            ValueError: If the ref is invalid or does not exist
        """
        if ref is None:
            default_branch = self.get_default_branch()
            return self._run_git("rev-parse", default_branch)
        
        ref = ref.strip()
        
        if self._is_valid_commit(ref):
            return self._run_git("rev-parse", ref)
        
        if self._is_valid_branch(ref):
            return self._run_git("rev-parse", ref)
        
        if self._is_valid_commit(ref[:7]):
            return self._run_git("rev-parse", ref[:7])
        
        raise ValueError(f"Invalid commit, branch, or shortened hash: {ref}")
    
    def _is_valid_commit(self, ref: str) -> bool:
        """Check if a reference is a valid commit."""
        try:
            self._run_git("cat-file", "-t", ref)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _is_valid_branch(self, ref: str) -> bool:
        """Check if a reference is a valid branch name."""
        try:
            self._run_git("rev-parse", "--verify", f"refs/heads/{ref}")
            return True
        except subprocess.CalledProcessError:
            try:
                self._run_git("rev-parse", "--verify", f"origin/{ref}")
                return True
            except subprocess.CalledProcessError:
                return False
    
    def get_commit_info(self, ref: Optional[str] = None) -> dict:
        """Get detailed commit information.
        
        Args:
            ref: Commit, branch, or None for default branch
            
        Returns:
            Dictionary with commit hash, message, author, date
        """
        commit_hash = self.get_commit_hash(ref)
        
        message = self._run_git("log", "-1", "--format=%s", commit_hash)
        full_message = self._run_git("log", "-1", "--format=%B", commit_hash)
        author = self._run_git("log", "-1", "--format=%an <%ae>", commit_hash)
        date = self._run_git("log", "-1", "--format=%ci", commit_hash)
        
        return {
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:7],
            "message": message,
            "full_message": full_message,
            "author": author,
            "date": date
        }


def extract_commit_hash(repo_path: str, ref: Optional[str] = None) -> str:
    """Convenience function to extract commit hash.
    
    Args:
        repo_path: Path to the cloned repository
        ref: Optional commit hash, branch name, or None for default branch
        
    Returns:
        Full commit hash (40 characters)
    """
    extractor = CommitHashExtractor(repo_path)
    return extractor.get_commit_hash(ref)


def extract_commit_info(repo_path: str, ref: Optional[str] = None) -> dict:
    """Convenience function to extract commit info.
    
    Args:
        repo_path: Path to the cloned repository
        ref: Optional commit hash, branch name, or None for default branch
        
    Returns:
        Dictionary with commit details
    """
    extractor = CommitHashExtractor(repo_path)
    return extractor.get_commit_info(ref)
