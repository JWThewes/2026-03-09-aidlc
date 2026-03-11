import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from src.code_review.github import (
    GitHubRepository,
    GitHubCloneError,
    RepositoryInfo,
    clone_repository,
    GITHUB_TOKEN_ENV,
)


class TestGitHubRepository:
    def test_parse_url_https_full(self):
        github = GitHubRepository()
        
        owner, repo = github.parse_repo_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_url_https_with_git(self):
        github = GitHubRepository()
        
        owner, repo = github.parse_repo_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_url_org_repo_format(self):
        github = GitHubRepository()
        
        owner, repo = github.parse_repo_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_url_org_repo_format_with_dashes(self):
        github = GitHubRepository()
        
        owner, repo = github.parse_repo_url("my-org/my-repo-name")
        assert owner == "my-org"
        assert repo == "my-repo-name"
    
    def test_parse_url_invalid(self):
        github = GitHubRepository()
        
        with pytest.raises(GitHubCloneError, match="Invalid repository"):
            github.parse_repo_url("not-a-valid-url")
    
    def test_parse_url_invalid_org_repo(self):
        github = GitHubRepository()
        
        with pytest.raises(GitHubCloneError, match="Invalid repo format"):
            github.parse_repo_url("owner/repo/extra")

    @patch("src.code_review.github.requests.Session")
    def test_get_repo_info_success(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo",
            "clone_url": "https://github.com/owner/repo.git",
            "default_branch": "main",
            "private": False
        }
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        github = GitHubRepository()
        repo_info = github.get_repo_info("owner", "repo")
        
        assert repo_info.owner == "owner"
        assert repo_info.repo == "repo"
        assert repo_info.default_branch == "main"
        assert repo_info.is_private is False

    @patch("src.code_review.github.requests.Session")
    def test_get_repo_info_not_found(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        github = GitHubRepository()
        
        with pytest.raises(GitHubCloneError, match="Repository not found"):
            github.get_repo_info("owner", "nonexistent")

    @patch("src.code_review.github.requests.Session")
    def test_get_repo_info_private_requires_auth(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = 403
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        github = GitHubRepository()
        
        with pytest.raises(GitHubCloneError, match="requires authentication"):
            github.get_repo_info("owner", "private-repo")


class TestCloneRepository:
    @patch("src.code_review.github.GitHubRepository.clone")
    @patch("src.code_review.github.GitHubRepository.get_commit_hash")
    def test_clone_repository_success(self, mock_commit_hash, mock_clone):
        mock_repo_path = Mock(spec=Path)
        mock_repo_info = RepositoryInfo(
            owner="test-owner",
            repo="test-repo",
            url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            default_branch="main",
            is_private=False
        )
        
        mock_clone.return_value = (mock_repo_path, mock_repo_info)
        mock_commit_hash.return_value = "abc123"
        
        result_path, result_hash, result_branch = clone_repository(
            "test-owner/test-repo"
        )
        
        assert result_path == mock_repo_path
        assert result_hash == "abc123"
        assert result_branch == "main"

    @patch.dict(os.environ, {GITHUB_TOKEN_ENV: "test-token"})
    @patch("src.code_review.github.GitHubRepository.clone")
    @patch("src.code_review.github.GitHubRepository.get_commit_hash")
    def test_clone_repository_uses_token_from_env(self, mock_commit_hash, mock_clone):
        mock_repo_path = Mock(spec=Path)
        mock_repo_info = RepositoryInfo(
            owner="test-owner",
            repo="test-repo",
            url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            default_branch="main",
            is_private=True
        )
        
        mock_clone.return_value = (mock_repo_path, mock_repo_info)
        mock_commit_hash.return_value = "abc123"
        
        with patch("src.code_review.github.GitHubRepository") as mock_github_class:
            mock_github_instance = Mock()
            mock_github_class.return_value = mock_github_instance
            mock_github_instance.clone.return_value = (mock_repo_path, mock_repo_info)
            mock_github_instance.get_commit_hash.return_value = "abc123"
            
            result_path, result_hash, result_branch = clone_repository(
                "test-owner/test-repo"
            )
            
            mock_github_class.assert_called_once_with(token="test-token")


class TestGitHubCloneError:
    def test_error_is_exception(self):
        error = GitHubCloneError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
