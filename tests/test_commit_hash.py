import pytest
import tempfile
import subprocess
from pathlib import Path
from code_review_agent.commit_hash import CommitHashExtractor, extract_commit_hash, extract_commit_info


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True
        )
        
        (repo_path / "test.txt").write_text("initial content")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True
        )
        
        subprocess.run(["git", "checkout", "-b", "feature-branch"], cwd=repo_path, check=True)
        (repo_path / "test.txt").write_text("feature content")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=repo_path,
            check=True
        )
        
        subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)
        
        yield repo_path


class TestCommitHashExtractor:
    def test_invalid_repo_path(self):
        with pytest.raises(ValueError, match="does not exist"):
            CommitHashExtractor("/nonexistent/path")
    
    def test_non_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Not a git repository"):
                CommitHashExtractor(tmpdir)
    
    def test_get_default_branch(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        default = extractor.get_default_branch()
        assert default in ["main", "master"]
    
    def test_get_commit_hash_default_branch(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        commit_hash = extractor.get_commit_hash()
        assert len(commit_hash) == 40
        assert commit_hash.isalnum()
    
    def test_get_commit_hash_specific_commit(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        commits = subprocess.run(
            ["git", "log", "--format=%H"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip().split("\n")
        
        commit_hash = extractor.get_commit_hash(commits[0])
        assert commit_hash == commits[0]
    
    def test_get_commit_hash_branch_name(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        commit_hash = extractor.get_commit_hash("feature-branch")
        assert len(commit_hash) == 40
        
        commits = subprocess.run(
            ["git", "log", "feature-branch", "--format=%H"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip().split("\n")
        assert commit_hash == commits[0]
    
    def test_get_commit_hash_short_commit(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        commits = subprocess.run(
            ["git", "log", "--format=%H"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip().split("\n")
        
        short_hash = commits[0][:7]
        commit_hash = extractor.get_commit_hash(short_hash)
        assert commit_hash == commits[0]
    
    def test_get_commit_hash_invalid_ref(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        with pytest.raises(ValueError, match="Invalid commit"):
            extractor.get_commit_hash("nonexistent-branch-12345")
    
    def test_get_commit_info(self, temp_repo):
        extractor = CommitHashExtractor(str(temp_repo))
        info = extractor.get_commit_info()
        
        assert "commit_hash" in info
        assert "short_hash" in info
        assert "message" in info
        assert "author" in info
        assert "date" in info
        assert len(info["commit_hash"]) == 40
        assert len(info["short_hash"]) == 7


class TestConvenienceFunctions:
    def test_extract_commit_hash(self, temp_repo):
        commit_hash = extract_commit_hash(str(temp_repo))
        assert len(commit_hash) == 40
    
    def test_extract_commit_hash_with_ref(self, temp_repo):
        commit_hash = extract_commit_hash(str(temp_repo), "main")
        assert len(commit_hash) == 40
    
    def test_extract_commit_info(self, temp_repo):
        info = extract_commit_info(str(temp_repo))
        assert "commit_hash" in info
        assert "message" in info
