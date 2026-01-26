"""
Docker runner for containerized evaluations.

This module provides Docker-based isolated execution for CodeGate.
It builds dependency images based on contract configuration and provides
utilities to run commands in sandboxed containers.

Responsibilities:
- Build deps image with system + Python dependencies
- Run arbitrary commands in containers with proper isolation
- Handle network restrictions from contract
"""

import subprocess
import tempfile
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


class DockerRunner:
    """
    Docker utility for building images and running containers.
    
    This class ONLY handles Docker operations:
    - Building dependency images from contract config
    - Running commands in isolated containers
    
    It does NOT contain rule-specific logic.
    """
    
    WORKSPACE_PATH = "/workspace"
    DEPS_IMAGE_PREFIX = "codegate-deps"
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Docker runner.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self._docker_available = None
        self._deps_image = None
    
    def is_available(self) -> bool:
        """Check if Docker is available and running."""
        if self._docker_available is None:
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                self._docker_available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._docker_available = False
        return self._docker_available
    
    def check_available(self) -> None:
        """Check if Docker is available, raise error if not."""
        if not self.is_available():
            raise RuntimeError(
                "Docker is not available or not running. "
                "Please install/start Docker to use Docker-based evaluations."
            )
    
    def build_deps_image(
        self,
        runtime_image: str,
        system_dependencies: List[str],
        python_dependencies: List[str],
        project_path: Optional[Path] = None,
        force_rebuild: bool = False
    ) -> str:
        """
        Build a dependency image with all required packages.
        
        This creates a reusable image with:
        - Base runtime image
        - System dependencies (apt packages)
        - Python dependencies (pip packages)
        
        The image is cached based on a hash of the configuration.
        
        Args:
            runtime_image: Base image from Environment.runtime_image
            system_dependencies: apt packages from Environment.system_dependencies
            python_dependencies: pip packages from project.python_dependencies
            project_path: Optional path to check for requirements.txt
            force_rebuild: Force rebuild even if image exists
            
        Returns:
            Image tag for the built deps image
        """
        self.check_available()
        
        # Generate unique image tag based on configuration
        config_hash = self._hash_config(runtime_image, system_dependencies, python_dependencies)
        image_tag = f"{self.DEPS_IMAGE_PREFIX}:{config_hash[:12]}"
        
        # Use cached image if available
        if not force_rebuild and self._image_exists(image_tag):
            if self.verbose:
                print(f"  Using cached deps image: {image_tag}")
            self._deps_image = image_tag
            return image_tag
        
        if self.verbose:
            print(f"  Building deps image: {image_tag}")
            print(f"    Base image: {runtime_image}")
            if system_dependencies:
                print(f"    System deps: {system_dependencies}")
            if python_dependencies:
                print(f"    Python deps: {python_dependencies}")
        
        # Create temp directory for build context
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Gather requirements
            requirements_content = ""
            # Read existing requirements.txt if present
            if project_path:
                req_file = project_path / "requirements.txt"
                if req_file.exists():
                    requirements_content = req_file.read_text()
            
            if python_dependencies:
                if requirements_content:
                    requirements_content += "\n"
                requirements_content += "\n".join(python_dependencies)
            
            # Write requirements.txt
            requirements_path = tmpdir_path / "requirements.txt"
            requirements_path.write_text(requirements_content)
            
            # Generate Dockerfile
            dockerfile_content = self._generate_dockerfile(
                runtime_image=runtime_image,
                system_dependencies=system_dependencies,
                has_requirements=bool(requirements_content.strip())
            )
            dockerfile_path = tmpdir_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            if self.verbose:
                print(f"    Dockerfile:\n{dockerfile_content}")
            
            # Build image
            build_cmd = [
                "docker", "build",
                "-t", image_tag,
                "-f", str(dockerfile_path),
                str(tmpdir_path)
            ]
            
            result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for deps
            )
            
            if result.returncode != 0:
                error_msg = self._parse_build_error(result.stderr)
                raise RuntimeError(f"Docker build failed: {error_msg}")
            
            if self.verbose:
                print(f"  Deps image built: {image_tag}")
            
            self._deps_image = image_tag
            return image_tag
    
    def run_command(
        self,
        image: str,
        command: List[str],
        project_path: Optional[Path] = None,
        network_access: bool = False,
        writable: bool = False,
        environment: Optional[Dict[str, str]] = None,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess:
        """
        Run a command in a Docker container.
        
        Args:
            image: Docker image to use
            command: Command to execute as list
            project_path: Path to mount as /workspace
            network_access: Allow network (from Environment.network_access)
            writable: Mount workspace as read-write (default read-only)
            environment: Additional environment variables
            timeout: Command timeout in seconds
            memory_limit: Container memory limit
            cpu_limit: Container CPU limit
            
        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        self.check_available()
        
        cmd = ["docker", "run", "--rm"]
        
        # Network isolation
        if not network_access:
            cmd.append("--network=none")
        
        
        # Mount project directory
        if project_path:
            mount_mode = "rw" if writable else "ro"
            cmd.extend(["-v", f"{project_path.resolve()}:{self.WORKSPACE_PATH}:{mount_mode}"])

        # Environment variables
        if environment:
            for k, v in environment.items():
                cmd.extend(["-e", f"{k}={v}"])

        # Command to run
        cmd.append(image)
        cmd.extend(command)

        # Execute
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def cleanup_image(self, image_tag: str) -> bool:
        """Remove a Docker image."""
        try:
            result = subprocess.run(
                ["docker", "rmi", image_tag],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _generate_dockerfile(
        self,
        runtime_image: str,
        system_dependencies: List[str],
        has_requirements: bool
    ) -> str:
        """Generate Dockerfile from contract configuration."""
        lines = [f"FROM {runtime_image}", ""]
        
        # System dependencies
        if system_dependencies:
            deps_str = " \\\n    ".join(system_dependencies)
            lines.extend([
                "# System dependencies from Environment.system_dependencies",
                "RUN apt-get update && apt-get install -y --no-install-recommends \\",
                f"    {deps_str} \\",
                "    && rm -rf /var/lib/apt/lists/*",
                ""
            ])
        
        # Upgrade pip
        lines.extend([
            "# Upgrade pip, setuptools, wheel",
            "RUN python -m pip install --upgrade pip setuptools wheel",
            ""
        ])
        
        # Python dependencies
        if has_requirements:
            lines.extend([
                "# Python dependencies from requirements.txt + project.python_dependencies",
                "COPY requirements.txt /tmp/requirements.txt",
                "RUN python -m pip install --no-input --disable-pip-version-check -r /tmp/requirements.txt",
                ""
            ])
        
        # Workspace
        lines.extend([
            f"WORKDIR {self.WORKSPACE_PATH}",
            ""
        ])
        
        return "\n".join(lines)
    
    def _hash_config(
        self,
        runtime_image: str,
        system_dependencies: List[str],
        python_dependencies: List[str]
    ) -> str:
        """Generate hash of config for image caching."""
        content = f"{runtime_image}|{','.join(sorted(system_dependencies))}|{','.join(sorted(python_dependencies))}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _image_exists(self, image_tag: str) -> bool:
        """Check if Docker image exists locally."""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_tag],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _parse_build_error(self, stderr: str) -> str:
        """Parse Docker build error for meaningful message."""
        lines = stderr.strip().split('\n')
        for line in lines:
            if "ERROR:" in line or "error:" in line.lower():
                return line.strip()
            if "Could not find" in line or "No matching distribution" in line:
                return line.strip()
        return stderr[-500:] if len(stderr) > 500 else stderr
