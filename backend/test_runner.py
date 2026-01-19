#!/usr/bin/env python
"""
Test runner script for iVote Systems
Provides convenient commands to run tests with various configurations
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ivs_backend.settings')

def run_command(cmd, description=""):
    """Run a shell command and report results"""
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    """Main test runner interface"""
    parser = argparse.ArgumentParser(
        description='iVote Systems Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py test_runner --all           # Run all tests with coverage
  python manage.py test_runner --unit          # Run unit tests only
  python manage.py test_runner --integration   # Run integration tests
  python manage.py test_runner --coverage      # Generate coverage report
  python manage.py test_runner --security      # Run security tests
        """
    )
    
    parser.add_argument('--all', action='store_true', help='Run all tests with coverage')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--fast', action='store_true', help='Run fast tests only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--failfast', '-f', action='store_true', help='Stop on first failure')
    parser.add_argument('--app', type=str, help='Run tests for specific app')
    parser.add_argument('--test', type=str, help='Run specific test module')
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd_parts = ['pytest']
    
    # Add verbosity
    if args.verbose:
        cmd_parts.append('-vv')
    else:
        cmd_parts.append('-v')
    
    # Add fail fast
    if args.failfast:
        cmd_parts.append('-x')
    
    # Add specific test paths
    if args.app:
        cmd_parts.append(f'{args.app}/')
    elif args.test:
        cmd_parts.append(f'{args.test}')
    
    # Add markers for test type
    if args.unit and not args.integration:
        cmd_parts.append('-m "unit"')
    elif args.integration and not args.unit:
        cmd_parts.append('-m "integration"')
    elif args.security:
        cmd_parts.append('-m "security"')
    elif args.fast:
        cmd_parts.append('-m "not slow"')
    
    # Add coverage
    if args.coverage or args.all:
        cmd_parts.extend([
            '--cov=accounts',
            '--cov=elections',
            '--cov=voting',
            '--cov=auditing',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-report=xml'
        ])
    
    cmd = ' '.join(cmd_parts)
    
    # Run tests
    if args.all:
        return run_command(cmd, "Running All Tests with Coverage")
    elif args.unit:
        return run_command(cmd, "Running Unit Tests")
    elif args.integration:
        return run_command(cmd, "Running Integration Tests")
    elif args.security:
        return run_command(cmd, "Running Security Tests")
    elif args.coverage:
        return run_command(cmd, "Generating Coverage Report")
    elif args.app:
        return run_command(cmd, f"Running Tests for {args.app}")
    elif args.test:
        return run_command(cmd, f"Running {args.test}")
    else:
        # Default: run all with coverage
        cmd_parts.extend([
            '--cov=accounts',
            '--cov=elections',
            '--cov=voting',
            '--cov=auditing',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
        cmd = ' '.join(cmd_parts)
        return run_command(cmd, "Running All Tests with Coverage (Default)")


if __name__ == '__main__':
    sys.exit(main())
