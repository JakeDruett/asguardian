#!/usr/bin/env bash
#
# publish-asgard.sh - Push the Asgard/ subtree to its standalone repository.
#
# Usage:
#   ./publish-asgard.sh [branch]
#
# Arguments:
#   branch   Target branch on the remote (default: main)
#
# This script must be run from the GAIA monorepo root directory.
# It uses git subtree push to publish the Asgard directory as a
# standalone repository at github.com/JakeDruett/asgard.

set -euo pipefail

REMOTE_NAME="asgard-standalone"
REMOTE_URL="git@github.com:JakeDruett/asgard.git"
SUBTREE_PREFIX="Asgard"
TARGET_BRANCH="${1:-main}"

# Verify we are in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "ERROR: Not inside a git repository."
    exit 1
fi

# Verify we are at the monorepo root (Asgard/ should exist here)
if [ ! -d "$SUBTREE_PREFIX" ]; then
    echo "ERROR: Directory '$SUBTREE_PREFIX' not found."
    echo "This script must be run from the GAIA monorepo root."
    exit 1
fi

# Add the remote if it does not already exist
if ! git remote get-url "$REMOTE_NAME" > /dev/null 2>&1; then
    echo "Adding remote '$REMOTE_NAME' -> $REMOTE_URL"
    git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "Pushing subtree '$SUBTREE_PREFIX' to '$REMOTE_NAME/$TARGET_BRANCH'..."
git subtree push --prefix="$SUBTREE_PREFIX" "$REMOTE_NAME" "$TARGET_BRANCH"

echo "Done. Asgard published to $REMOTE_URL ($TARGET_BRANCH)."
