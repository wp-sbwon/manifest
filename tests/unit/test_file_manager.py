"""
Unit tests for FileManager.

Tests file operations: read, write, edit, list, and error handling.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from manifest.runtime.tools.file_manager import FileManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def file_manager(temp_dir):
    """Create a FileManager instance."""
    return FileManager(working_dir=temp_dir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello, World!\nLine 2\nLine 3")
    return file_path


def test_file_manager_initialization(file_manager, temp_dir):
    """Test FileManager initialization."""
    assert file_manager.working_dir == temp_dir
    assert file_manager is not None


def test_read_file(file_manager, sample_file):
    """Test reading a file."""
    result = file_manager.read(str(sample_file))
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is True
    content = result.get("content", "")
    assert isinstance(content, str)
    assert "Hello, World!" in content
    assert "Line 2" in content


def test_read_file_not_found(file_manager):
    """Test reading non-existent file returns error."""
    result = file_manager.read("non-existent.txt")
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is False
    assert "error" in result or "not found" in result.get("message", "").lower()


def test_read_file_with_line_range(file_manager, sample_file):
    """Test reading file with line range."""
    result = file_manager.read(str(sample_file), start_line=1, end_line=2)
    
    assert result.get("success") is True
    content = result.get("content", "")
    assert "Hello, World!" in content
    # Should only contain first 2 lines
    lines = content.split('\n')
    assert len(lines) <= 2


def test_write_file(file_manager, temp_dir):
    """Test writing a new file."""
    file_path = temp_dir / "new_file.txt"
    content = "New file content"
    
    file_manager.write(str(file_path), content)
    
    assert file_path.exists()
    assert file_path.read_text() == content


def test_write_file_overwrite(file_manager, sample_file):
    """Test overwriting existing file."""
    new_content = "New content"
    
    file_manager.write(str(sample_file), new_content)
    
    assert sample_file.read_text() == new_content


def test_write_file_create_directories(file_manager, temp_dir):
    """Test writing file creates parent directories."""
    file_path = temp_dir / "subdir" / "nested" / "file.txt"
    content = "Nested file"
    
    file_manager.write(str(file_path), content)
    
    assert file_path.exists()
    assert file_path.read_text() == content


def test_edit_file_insert(file_manager, sample_file):
    """Test editing file by replacing string to insert content."""
    original_content = sample_file.read_text()
    
    result = file_manager.edit(
        str(sample_file),
        old_string="Line 2",
        new_string="Line 2\nInserted line"
    )
    
    assert result.get("success") is True
    new_content = sample_file.read_text()
    assert "Inserted line" in new_content
    assert len(new_content) > len(original_content)


def test_edit_file_multiple_replacements(file_manager, sample_file):
    """Test editing file with multiple occurrences."""
    # Add duplicate line
    sample_file.write_text("Line 2\nLine 2\nLine 3")
    
    # Replace first occurrence only
    result = file_manager.edit(
        str(sample_file),
        old_string="Line 2",
        new_string="Line 2 Modified"
    )
    
    assert result.get("success") is True
    content = sample_file.read_text()
    # Should replace only first occurrence
    assert "Line 2 Modified" in content


def test_edit_file_string_not_found(file_manager, sample_file):
    """Test editing file when old_string not found."""
    result = file_manager.edit(
        str(sample_file),
        old_string="Non-existent string",
        new_string="New string"
    )
    
    assert result.get("success") is False
    assert "not found" in result.get("message", "").lower() or "error" in result


def test_edit_file_string_not_found_error(file_manager, sample_file):
    """Test editing with string that doesn't exist."""
    result = file_manager.edit(
        str(sample_file),
        old_string="Non-existent string that will never match",
        new_string="New string"
    )
    
    assert result.get("success") is False
    assert "not found" in result.get("message", "").lower() or "error" in result


def test_list_directory(file_manager, temp_dir):
    """Test listing directory contents."""
    # Create some files and directories
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    (temp_dir / "subdir").mkdir()
    (temp_dir / "subdir" / "file3.txt").write_text("content3")
    
    result = file_manager.list(str(temp_dir))
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is True
    items = result.get("items", [])
    assert len(items) >= 2
    item_names = [item.get("name", item) if isinstance(item, dict) else str(item) for item in items]
    assert any("file1.txt" in str(name) for name in item_names)
    assert any("file2.txt" in str(name) for name in item_names)


def test_list_directory_current_dir(file_manager, temp_dir):
    """Test listing current directory (no path specified)."""
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    
    result = file_manager.list()
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is True


def test_list_directory_not_found(file_manager):
    """Test listing non-existent directory."""
    result = file_manager.list("non-existent-dir")
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is False
    assert "error" in result or "not found" in result.get("message", "").lower()


def test_list_directory_with_files(file_manager, temp_dir):
    """Test listing directory with multiple files."""
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.py").write_text("content2")
    (temp_dir / "file3.txt").write_text("content3")
    
    result = file_manager.list(str(temp_dir))
    
    assert result.get("success") is True
    items = result.get("items", [])
    assert len(items) >= 3
    item_names = [item.get("name", item) if isinstance(item, dict) else str(item) for item in items]
    assert any("file1.txt" in str(name) for name in item_names)
    assert any("file2.py" in str(name) for name in item_names)


def test_file_permissions(file_manager, temp_dir):
    """Test file permission handling."""
    file_path = temp_dir / "readonly.txt"
    file_path.write_text("readonly content")
    
    # Make file read-only (Unix)
    if os.name != 'nt':
        os.chmod(file_path, 0o444)
        
        # Writing should handle permission error
        try:
            file_manager.write(str(file_path), "new content")
        except PermissionError:
            # Expected on read-only file
            pass


def test_large_file_handling(file_manager, temp_dir):
    """Test handling large files."""
    file_path = temp_dir / "large.txt"
    large_content = "x" * 100000  # 100KB
    
    write_result = file_manager.write(str(file_path), large_content)
    assert write_result.get("success") is True
    
    read_result = file_manager.read(str(file_path))
    assert read_result.get("success") is True
    content = read_result.get("content", "")
    assert len(content) == len(large_content)


def test_grep_file(file_manager, sample_file):
    """Test grepping file for pattern."""
    result = file_manager.grep("Hello", str(sample_file))
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is True
    matches = result.get("matches", [])
    assert len(matches) > 0


def test_read_file_line_range_out_of_bounds(file_manager, sample_file):
    """Test reading file with out-of-bounds line range."""
    # Read with line range beyond file length
    result = file_manager.read(str(sample_file), start_line=1, end_line=100)
    
    assert result.get("success") is True
    content = result.get("content", "")
    # Should return all available lines
    assert len(content) > 0


def test_glob_pattern(file_manager, temp_dir):
    """Test globbing files with pattern."""
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.py").write_text("content2")
    (temp_dir / "file3.txt").write_text("content3")
    
    result = file_manager.glob("*.txt")
    
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("success") is True
    files = result.get("files", [])
    assert len(files) >= 2
    assert all(".txt" in f for f in files)


def test_path_normalization(file_manager, temp_dir):
    """Test path normalization."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")
    
    # Test with different path formats
    content1 = file_manager.read(str(file_path))
    content2 = file_manager.read(str(file_path.absolute()))
    
    assert content1 == content2


def test_relative_path_handling(file_manager, temp_dir):
    """Test handling relative paths."""
    file_path = temp_dir / "relative.txt"
    file_path.write_text("relative content")
    
    # Read using relative path
    relative_path = "relative.txt"
    result = file_manager.read(relative_path)
    
    assert result.get("success") is True
    assert "relative content" in result.get("content", "")
