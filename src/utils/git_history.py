"""
Git history utilities for tracking item changes.

This module provides functions to extract change history from git,
including status changes, author information, and timestamps.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


def get_item_history(item_path: Path, dhf_root: Path) -> List[Dict]:
    """
    Get the complete git history for an item file.
    
    Args:
        item_path: Path to the item YAML file
        dhf_root: Root directory of the DHF
        
    Returns:
        List of commit dictionaries with keys:
        - commit_hash: Git commit SHA
        - author_name: Name of the committer
        - author_email: Email of the committer
        - timestamp: ISO format timestamp
        - message: Commit message
        - changes: Dict of field changes (if available)
    """
    # Get relative path from git root
    try:
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=dhf_root,
            text=True
        ).strip()
        rel_path = item_path.relative_to(git_root)
    except (subprocess.CalledProcessError, ValueError):
        return []
    
    # Get commit history
    try:
        log_output = subprocess.check_output(
            ['git', 'log', '--follow', '--pretty=format:%H|%an|%ae|%ai|%s', '--', str(rel_path)],
            cwd=git_root,
            text=True
        )
    except subprocess.CalledProcessError:
        return []
    
    if not log_output:
        return []
    
    commits = []
    for line in log_output.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|', 4)
        if len(parts) == 5:
            commits.append({
                'commit_hash': parts[0],
                'author_name': parts[1],
                'author_email': parts[2],
                'timestamp': parts[3],
                'message': parts[4]
            })
    
    return commits


def get_status_changes(item_path: Path, dhf_root: Path) -> List[Dict]:
    """
    Get the history of status changes for an item.
    
    Args:
        item_path: Path to the item YAML file
        dhf_root: Root directory of the DHF
        
    Returns:
        List of status change dictionaries with keys:
        - from_status: Previous status (None if new)
        - to_status: New status
        - author_name: Name of the committer
        - author_email: Email of the committer
        - timestamp: ISO format timestamp
        - commit_hash: Git commit SHA
        - message: Commit message
    """
    # Get relative path from git root
    try:
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=dhf_root,
            text=True
        ).strip()
        rel_path = item_path.relative_to(git_root)
    except (subprocess.CalledProcessError, ValueError):
        return []
    
    # Get commit history with patches
    try:
        log_output = subprocess.check_output(
            ['git', 'log', '--follow', '-p', '--pretty=format:COMMIT|%H|%an|%ae|%ai|%s', '--', str(rel_path)],
            cwd=git_root,
            text=True
        )
    except subprocess.CalledProcessError:
        return []
    
    if not log_output:
        return []
    
    # Parse commits and look for status changes
    status_changes = []
    current_commit = None
    
    for line in log_output.split('\n'):
        # New commit marker
        if line.startswith('COMMIT|'):
            parts = line[7:].split('|', 4)
            if len(parts) == 5:
                current_commit = {
                    'commit_hash': parts[0],
                    'author_name': parts[1],
                    'author_email': parts[2],
                    'timestamp': parts[3],
                    'message': parts[4]
                }
        
        # Look for status changes in diff
        elif current_commit and line.startswith('-status:'):
            old_status = line.split(':', 1)[1].strip()
            current_commit['from_status'] = old_status
        elif current_commit and line.startswith('+status:'):
            new_status = line.split(':', 1)[1].strip()
            current_commit['to_status'] = new_status
            
            # If we have both old and new status, record the change
            if 'from_status' in current_commit:
                status_changes.append({
                    'from_status': current_commit['from_status'],
                    'to_status': current_commit['to_status'],
                    'author_name': current_commit['author_name'],
                    'author_email': current_commit['author_email'],
                    'timestamp': current_commit['timestamp'],
                    'commit_hash': current_commit['commit_hash'],
                    'message': current_commit['message']
                })
                # Reset for next change
                current_commit = dict(current_commit)
                del current_commit['from_status']
                del current_commit['to_status']
            elif 'to_status' in current_commit:
                # New item with initial status
                status_changes.append({
                    'from_status': None,
                    'to_status': current_commit['to_status'],
                    'author_name': current_commit['author_name'],
                    'author_email': current_commit['author_email'],
                    'timestamp': current_commit['timestamp'],
                    'commit_hash': current_commit['commit_hash'],
                    'message': current_commit['message']
                })
    
    # Reverse to get chronological order (oldest first)
    return list(reversed(status_changes))


def get_field_changes(item_path: Path, dhf_root: Path, field_name: str) -> List[Dict]:
    """
    Get the history of changes for a specific field in an item.
    
    Args:
        item_path: Path to the item YAML file
        dhf_root: Root directory of the DHF
        field_name: Name of the field to track (e.g., 'status', 'title')
        
    Returns:
        List of field change dictionaries with keys:
        - from_value: Previous value (None if new)
        - to_value: New value
        - author_name: Name of the committer
        - author_email: Email of the committer
        - timestamp: ISO format timestamp
        - commit_hash: Git commit SHA
        - message: Commit message
    """
    # Get relative path from git root
    try:
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=dhf_root,
            text=True
        ).strip()
        rel_path = item_path.relative_to(git_root)
    except (subprocess.CalledProcessError, ValueError):
        return []
    
    # Get commit history with patches
    try:
        log_output = subprocess.check_output(
            ['git', 'log', '--follow', '-p', '--pretty=format:COMMIT|%H|%an|%ae|%ai|%s', '--', str(rel_path)],
            cwd=git_root,
            text=True
        )
    except subprocess.CalledProcessError:
        return []
    
    if not log_output:
        return []
    
    # Parse commits and look for field changes
    field_changes = []
    current_commit = None
    field_pattern = f'^[+-]{field_name}:'
    
    for line in log_output.split('\n'):
        # New commit marker
        if line.startswith('COMMIT|'):
            parts = line[7:].split('|', 4)
            if len(parts) == 5:
                current_commit = {
                    'commit_hash': parts[0],
                    'author_name': parts[1],
                    'author_email': parts[2],
                    'timestamp': parts[3],
                    'message': parts[4]
                }
        
        # Look for field changes in diff
        elif current_commit and re.match(field_pattern, line):
            if line.startswith('-'):
                old_value = line.split(':', 1)[1].strip()
                current_commit['from_value'] = old_value
            elif line.startswith('+'):
                new_value = line.split(':', 1)[1].strip()
                current_commit['to_value'] = new_value
                
                # Record the change
                field_changes.append({
                    'from_value': current_commit.get('from_value'),
                    'to_value': current_commit['to_value'],
                    'author_name': current_commit['author_name'],
                    'author_email': current_commit['author_email'],
                    'timestamp': current_commit['timestamp'],
                    'commit_hash': current_commit['commit_hash'],
                    'message': current_commit['message']
                })
                # Reset for next change
                current_commit = dict(current_commit)
                if 'from_value' in current_commit:
                    del current_commit['from_value']
                if 'to_value' in current_commit:
                    del current_commit['to_value']
    
    # Reverse to get chronological order (oldest first)
    return list(reversed(field_changes))


def format_history_table(changes: List[Dict], change_type: str = "status") -> str:
    """
    Format change history as a markdown table.
    
    Args:
        changes: List of change dictionaries
        change_type: Type of change (e.g., "status", "field")
        
    Returns:
        Markdown formatted table string
    """
    if not changes:
        return f"No {change_type} changes found."
    
    lines = []
    lines.append(f"| Timestamp | Author | From | To | Commit | Message |")
    lines.append(f"|-----------|--------|------|-----|--------|---------|")
    
    for change in changes:
        timestamp = change['timestamp'][:19]  # Trim timezone for readability
        author = change['author_name']
        from_val = change.get('from_status') or change.get('from_value') or '(new)'
        to_val = change.get('to_status') or change.get('to_value', '')
        commit = change['commit_hash'][:7]
        message = change['message'][:50] + ('...' if len(change['message']) > 50 else '')
        
        lines.append(f"| {timestamp} | {author} | {from_val} | {to_val} | {commit} | {message} |")
    
    return '\n'.join(lines)
