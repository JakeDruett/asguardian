"""
L1 Integration Test Fixtures for Heimdall

Provides sample Python projects for integration testing.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def simple_project(tmp_path):
    """Create a simple Python project with basic structure."""
    project_dir = tmp_path / "simple_project"
    project_dir.mkdir()

    # Create a simple module
    (project_dir / "main.py").write_text('''
"""Main module."""
import os
import sys

def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

def calculate_product(a, b):
    """Calculate product of two numbers."""
    return a * b

if __name__ == "__main__":
    print(calculate_sum(5, 3))
''')

    # Create a service module
    (project_dir / "service.py").write_text('''
"""Service module."""
from typing import List, Optional

class DataService:
    """Service for data operations."""

    def __init__(self):
        self.data = []

    def add_item(self, item: str) -> None:
        """Add item to data."""
        self.data.append(item)

    def get_items(self) -> List[str]:
        """Get all items."""
        return self.data

    def find_item(self, query: str) -> Optional[str]:
        """Find an item by query."""
        for item in self.data:
            if query in item:
                return item
        return None
''')

    return project_dir


@pytest.fixture
def complex_project(tmp_path):
    """Create a complex Python project with multiple modules and dependencies."""
    project_dir = tmp_path / "complex_project"
    project_dir.mkdir()

    # Create package structure
    pkg_dir = project_dir / "mypackage"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('')

    # Create base module
    (pkg_dir / "base.py").write_text('''
"""Base classes."""
from abc import ABC, abstractmethod

class BaseService(ABC):
    """Abstract base service."""

    @abstractmethod
    def process(self, data):
        """Process data."""
        pass

    @abstractmethod
    def validate(self, data):
        """Validate data."""
        pass
''')

    # Create user service
    (pkg_dir / "user_service.py").write_text('''
"""User service module."""
from mypackage.base import BaseService
from mypackage.models import User

class UserService(BaseService):
    """Service for user operations."""

    def __init__(self):
        self.users = {}

    def process(self, data):
        """Process user data."""
        return self.create_user(data)

    def validate(self, data):
        """Validate user data."""
        required = ['username', 'email']
        return all(key in data for key in required)

    def create_user(self, data):
        """Create a new user."""
        if self.validate(data):
            user = User(data['username'], data['email'])
            self.users[user.username] = user
            return user
        return None

    def get_user(self, username):
        """Get user by username."""
        return self.users.get(username)
''')

    # Create models
    (pkg_dir / "models.py").write_text('''
"""Data models."""

class User:
    """User model."""

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'username': self.username,
            'email': self.email
        }
''')

    # Create utils with duplication
    (pkg_dir / "utils.py").write_text('''
"""Utility functions."""

def format_name(first, last):
    """Format full name."""
    return f"{first} {last}".strip()

def format_address(street, city, state, zip_code):
    """Format full address."""
    return f"{street}, {city}, {state} {zip_code}".strip()

def format_phone(area_code, number):
    """Format phone number."""
    return f"({area_code}) {number}".strip()
''')

    return project_dir


@pytest.fixture
def god_class_project(tmp_path):
    """Create a project with a god class for architecture testing."""
    project_dir = tmp_path / "god_class_project"
    project_dir.mkdir()

    (project_dir / "god_class.py").write_text('''
"""Module with a god class."""

class ApplicationManager:
    """Manages everything in the application."""

    def __init__(self):
        self.users = {}
        self.products = {}
        self.orders = {}
        self.config = {}

    # User management
    def create_user(self, username, email, password):
        """Create a new user."""
        self.users[username] = {'email': email, 'password': password}

    def delete_user(self, username):
        """Delete a user."""
        if username in self.users:
            del self.users[username]

    def update_user(self, username, **kwargs):
        """Update user details."""
        if username in self.users:
            self.users[username].update(kwargs)

    # Product management
    def add_product(self, product_id, name, price):
        """Add a product."""
        self.products[product_id] = {'name': name, 'price': price}

    def remove_product(self, product_id):
        """Remove a product."""
        if product_id in self.products:
            del self.products[product_id]

    def update_product(self, product_id, **kwargs):
        """Update product details."""
        if product_id in self.products:
            self.products[product_id].update(kwargs)

    # Order management
    def create_order(self, order_id, user, products):
        """Create a new order."""
        self.orders[order_id] = {'user': user, 'products': products}

    def cancel_order(self, order_id):
        """Cancel an order."""
        if order_id in self.orders:
            del self.orders[order_id]

    def update_order_status(self, order_id, status):
        """Update order status."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = status

    # Database operations
    def save_to_database(self, table, data):
        """Save data to database."""
        pass

    def query_database(self, query):
        """Query database."""
        pass

    # Email operations
    def send_email(self, to, subject, body):
        """Send email."""
        pass

    def send_notification(self, user, message):
        """Send notification."""
        pass

    # Reporting
    def generate_user_report(self):
        """Generate user report."""
        pass

    def generate_sales_report(self):
        """Generate sales report."""
        pass

    # Configuration
    def load_config(self, filename):
        """Load configuration."""
        pass

    def save_config(self, filename):
        """Save configuration."""
        pass
''')

    return project_dir


@pytest.fixture
def circular_dependency_project(tmp_path):
    """Create a project with circular dependencies."""
    project_dir = tmp_path / "circular_project"
    project_dir.mkdir()

    pkg_dir = project_dir / "circpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('')

    # Module A depends on B
    (pkg_dir / "module_a.py").write_text('''
"""Module A."""
from circpkg.module_b import function_b

def function_a():
    """Function A calls function B."""
    return function_b() + " and A"
''')

    # Module B depends on A
    (pkg_dir / "module_b.py").write_text('''
"""Module B."""
from circpkg.module_a import function_a

def function_b():
    """Function B calls function A."""
    return "B"
''')

    return project_dir


@pytest.fixture
def security_vulnerable_project(tmp_path):
    """Create a project with security vulnerabilities."""
    project_dir = tmp_path / "vulnerable_project"
    project_dir.mkdir()

    # Code with secrets
    (project_dir / "config.py").write_text('''
"""Configuration with secrets."""

API_KEY = "sk_fake_test_key_not_real_0000000"
DATABASE_PASSWORD = "SuperSecret123!"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

def get_database_url():
    """Get database URL."""
    return f"postgresql://admin:{DATABASE_PASSWORD}@localhost/mydb"
''')

    # Code with SQL injection vulnerability
    (project_dir / "database.py").write_text('''
"""Database operations."""
import sqlite3

def get_user_by_name(name):
    """Get user by name - SQL injection vulnerable."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{name}'"
    cursor.execute(query)
    return cursor.fetchone()

def search_products(keyword):
    """Search products - SQL injection vulnerable."""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + keyword + "%'")
    return cursor.fetchall()
''')

    # Code with command injection vulnerability
    (project_dir / "system.py").write_text('''
"""System operations."""
import os
import subprocess

def ping_host(hostname):
    """Ping a host - command injection vulnerable."""
    os.system(f"ping -c 1 {hostname}")

def backup_file(filename):
    """Backup a file - command injection vulnerable."""
    subprocess.call(f"cp {filename} {filename}.bak", shell=True)
''')

    return project_dir


@pytest.fixture
def inheritance_hierarchy_project(tmp_path):
    """Create a project with deep inheritance hierarchy."""
    project_dir = tmp_path / "inheritance_project"
    project_dir.mkdir()

    (project_dir / "hierarchy.py").write_text('''
"""Module with deep inheritance hierarchy."""

class Level1:
    """Base level 1."""
    def method_1(self):
        """Method 1."""
        pass

class Level2(Level1):
    """Level 2 inherits from Level1."""
    def method_2(self):
        """Method 2."""
        pass

class Level3(Level2):
    """Level 3 inherits from Level2."""
    def method_3(self):
        """Method 3."""
        pass

class Level4(Level3):
    """Level 4 inherits from Level3."""
    def method_4(self):
        """Method 4."""
        pass

class Level5(Level4):
    """Level 5 inherits from Level4."""
    def method_5(self):
        """Method 5."""
        pass

class Level6(Level5):
    """Level 6 inherits from Level5."""
    def method_6(self):
        """Method 6."""
        pass
''')

    # Create a class with high coupling
    (project_dir / "coupled.py").write_text('''
"""Module with highly coupled classes."""
from hierarchy import Level1, Level2, Level3, Level4, Level5, Level6

class HighlyCoupled:
    """Class with many dependencies."""

    def __init__(self):
        self.l1 = Level1()
        self.l2 = Level2()
        self.l3 = Level3()
        self.l4 = Level4()
        self.l5 = Level5()
        self.l6 = Level6()

    def use_all(self):
        """Use all dependencies."""
        self.l1.method_1()
        self.l2.method_2()
        self.l3.method_3()
        self.l4.method_4()
        self.l5.method_5()
        self.l6.method_6()
''')

    return project_dir


@pytest.fixture
def high_complexity_project(tmp_path):
    """Create a project with high cyclomatic complexity."""
    project_dir = tmp_path / "complex_functions_project"
    project_dir.mkdir()

    (project_dir / "complex.py").write_text('''
"""Module with high complexity functions."""

def process_data(data, mode, validate, transform, log):
    """Process data with many branches."""
    result = None

    if data is None:
        return None

    if mode == "fast":
        if validate:
            if not is_valid(data):
                if log:
                    print("Invalid data")
                return None
        if transform:
            data = transform_data(data)
        result = fast_process(data)
    elif mode == "slow":
        if validate:
            if not is_valid(data):
                if log:
                    print("Invalid data")
                return None
        if transform:
            data = transform_data(data)
        result = slow_process(data)
    elif mode == "balanced":
        if validate:
            if not is_valid(data):
                if log:
                    print("Invalid data")
                return None
        if transform:
            data = transform_data(data)
        result = balanced_process(data)
    else:
        if log:
            print(f"Unknown mode: {mode}")
        return None

    if result is not None:
        if log:
            print(f"Processed: {result}")
        return result
    else:
        if log:
            print("Processing failed")
        return None

def is_valid(data):
    """Check if data is valid."""
    return data is not None

def transform_data(data):
    """Transform data."""
    return data

def fast_process(data):
    """Fast processing."""
    return data

def slow_process(data):
    """Slow processing."""
    return data

def balanced_process(data):
    """Balanced processing."""
    return data
''')

    return project_dir
