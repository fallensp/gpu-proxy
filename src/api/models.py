"""
API models for the GPU Proxy API.
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str

class InstanceCreate(BaseModel):
    """Model for creating a new instance."""
    id: int = Field(..., description="Offer ID to create instance from")
    image: Optional[str] = Field(None, description="Docker image to use")
    onstart: Optional[str] = Field(None, description="Command to run on instance start")
    disk: Optional[Union[int, str]] = Field(None, description="Disk space in GB")
    price: Optional[Union[float, str]] = Field(None, description="Bid price in $/hour")
    label: Optional[str] = Field(None, description="Label for the instance")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    jupyter: Optional[bool] = Field(None, description="Whether to start a Jupyter server")
    jupyter_dir: Optional[str] = Field(None, description="Directory to start Jupyter in")
    jupyter_lab: Optional[bool] = Field(None, description="Whether to start JupyterLab")
    python_version: Optional[str] = Field(None, description="Python version to use")
    docker_args: Optional[str] = Field(None, description="Docker arguments")
    docker_cmd: Optional[str] = Field(None, description="Docker command")
    docker_image: Optional[str] = Field(None, description="Docker image")
    runtype: Optional[str] = Field(None, description="Run type (e.g., 'jupyter', 'ssh')")
    create_schedule: Optional[bool] = Field(None, description="Whether to create a schedule for this instance")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule data for automatic start/stop")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional options")
    docker_env: Optional[Dict[str, Any]] = None

class InstanceBidChange(BaseModel):
    """Model for changing the bid price of an instance."""
    price: float = Field(..., description="New bid price in $/hour")

class InstanceLabel(BaseModel):
    """Model for labeling an instance."""
    label: str = Field(..., description="Label to assign to the instance")

class SearchFilters(BaseModel):
    """Model for search filters."""
    # GPU-related filters
    min_gpus: Optional[int] = Field(None, description="Minimum number of GPUs")
    max_gpus: Optional[int] = Field(None, description="Maximum number of GPUs")
    gpu_name: Optional[str] = Field(None, description="GPU model name (e.g., 'RTX 4090', 'A100')")
    gpu_ram: Optional[float] = Field(None, description="Minimum GPU RAM in GB")
    cuda_vers: Optional[float] = Field(None, description="Minimum CUDA version")
    pci_gen: Optional[int] = Field(None, description="Minimum PCI generation")
    gpu_mem_bw: Optional[float] = Field(None, description="Minimum GPU memory bandwidth in GB/s")
    flops: Optional[float] = Field(None, description="Minimum FLOPS in TFLOPS")
    
    # System-related filters
    disk_space: Optional[int] = Field(None, description="Minimum disk space in GB")
    ram: Optional[float] = Field(None, description="Minimum system RAM in GB")
    inet_up: Optional[float] = Field(None, description="Minimum upload bandwidth in Mbps")
    inet_down: Optional[float] = Field(None, description="Minimum download bandwidth in Mbps")
    reliability: Optional[float] = Field(None, description="Minimum reliability score (0-1)")
    dlperf: Optional[float] = Field(None, description="Minimum DL performance score")
    dlperf_usd: Optional[float] = Field(None, description="Minimum DL performance per dollar")
    num_cpus: Optional[int] = Field(None, description="Minimum number of CPU cores")
    
    # Pricing and availability filters
    max_price: Optional[float] = Field(None, description="Maximum price per GPU in $/hour")
    min_bid: Optional[float] = Field(None, description="Minimum bid price in $/hour")
    verified: Optional[bool] = Field(None, description="Only verified hosts")
    external: Optional[bool] = Field(None, description="Include external offers")
    order: Optional[str] = Field(None, description="Order results by field (e.g., 'score', 'price', 'dlperf_usd')")
    disable_bundling: Optional[bool] = Field(None, description="Disable bundling of multiple GPUs")
    
    # Additional filters
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional filters not covered above")

class InstanceSearchFilters(BaseModel):
    """Model for filtering user's rented instances."""
    instance_id: Optional[int] = Field(None, description="Filter by instance ID")
    machine_id: Optional[int] = Field(None, description="Filter by machine ID")
    gpu_name: Optional[str] = Field(None, description="Filter by GPU name (e.g., 'RTX 4090')")
    num_gpus: Optional[int] = Field(None, description="Filter by number of GPUs")
    ssh_host: Optional[str] = Field(None, description="Filter by SSH hostname")
    ssh_port: Optional[int] = Field(None, description="Filter by SSH port")
    label: Optional[str] = Field(None, description="Filter by instance label")
    status: Optional[str] = Field(None, description="Filter by status (e.g., 'running', 'stopped')")
    image: Optional[str] = Field(None, description="Filter by Docker image")
    disk_space: Optional[int] = Field(None, description="Filter by disk space in GB")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional filters not covered above")

class AutoscalerCreate(BaseModel):
    """Model for creating a new autoscaler group."""
    min_load: Optional[float] = Field(None, description="Minimum floor load in perf units/s (token/s for LLMs)")
    target_util: Optional[float] = Field(0.9, description="Target capacity utilization (fraction, max 1.0)")
    cold_mult: Optional[float] = Field(2.5, description="Cold/stopped instance capacity target as multiple of hot capacity target")
    gpu_ram: Optional[float] = Field(None, description="Estimated GPU RAM requirement in GB")
    template_hash: Optional[str] = Field(None, description="Template hash (optional)")
    template_id: Optional[int] = Field(None, description="Template ID (optional)")
    search_params: str = Field(..., description="Search parameters string for finding instances (e.g., 'gpu_ram>=23 num_gpus=2')")
    launch_args: str = Field(..., description="Launch arguments string for creating instances")
    endpoint_name: Optional[str] = Field(None, description="Deployment endpoint name")

class SearchOffersParams(BaseModel):
    """Model for search offers parameters."""
    query: Optional[str] = Field(None, description="Custom query string (e.g., 'gpu_name=RTX_4090 num_gpus>=2')")
    type: Optional[str] = Field("on-demand", description="Pricing type: 'on-demand', 'reserved', or 'bid'")
    disable_bundling: Optional[bool] = Field(False, description="Show identical offers")
    storage: Optional[float] = Field(5.0, description="Amount of storage to use for pricing, in GiB")
    order: Optional[str] = Field("score-", description="Comma-separated list of fields to sort on")
    no_default: Optional[bool] = Field(False, description="Disable default query")

class InstanceTemplateCreate(BaseModel):
    """Model for creating an instance template."""
    name: str = Field(..., description="Name of the template")
    description: Optional[str] = Field(None, description="Description of what the template is for")
    image: str = Field(..., description="Docker image to use for the instance")
    env_params: Optional[str] = Field(None, description="Environment parameters for the Docker container")
    onstart_cmd: Optional[str] = Field(None, description="Command to run when the instance starts")
    disk_size: Optional[int] = Field(50, description="Disk size in GB")
    use_ssh: Optional[bool] = Field(True, description="Whether to enable SSH access")
    use_direct: Optional[bool] = Field(True, description="Whether to use direct connection")
    other_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    template_type: Optional[str] = Field("user", description="Type of template (user, system, etc.)")
    tags: Optional[List[str]] = Field(None, description="Tags for categorizing templates")
    is_public: Optional[bool] = Field(False, description="Whether the template is public")

class InstanceTemplateUpdate(BaseModel):
    """Model for updating an instance template."""
    name: Optional[str] = Field(None, description="Name of the template")
    description: Optional[str] = Field(None, description="Description of what the template is for")
    image: Optional[str] = Field(None, description="Docker image to use for the instance")
    env_params: Optional[str] = Field(None, description="Environment parameters for the Docker container")
    onstart_cmd: Optional[str] = Field(None, description="Command to run when the instance starts")
    disk_size: Optional[int] = Field(None, description="Disk size in GB")
    use_ssh: Optional[bool] = Field(None, description="Whether to enable SSH access")
    use_direct: Optional[bool] = Field(None, description="Whether to use direct connection")
    other_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    template_type: Optional[str] = Field(None, description="Type of template (user, system, etc.)")
    tags: Optional[List[str]] = Field(None, description="Tags for categorizing templates")
    is_public: Optional[bool] = Field(None, description="Whether the template is public")
    is_featured: Optional[bool] = Field(None, description="Whether the template is featured") 