# GPU Proxy for Vast.ai

This project implements a Python-based REST API for interacting with Vast.ai GPU resources using the official Vast.ai Python SDK. The API provides a clean interface for managing GPU instances and can be consumed by any frontend application.

## Getting Started

### Prerequisites

- Python 3.8 or later
- Vast.ai account and API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd gpu-proxy

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the root directory with your Vast.ai API key and other configuration:

```
# Vast.ai API Key
VAST_API_KEY=your_api_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
```

## Usage

### Running the API Server

```bash
# Run the API server
python run.py
```

The API will be available at http://localhost:8000 with Swagger documentation at http://localhost:8000/docs.

### API Endpoints

The API provides the following endpoints:

- `GET /api/v1/instances` - List available GPU instances
- `GET /api/v1/my-instances` - Show your currently rented instances
- `POST /api/v1/instances` - Create a new instance
- `DELETE /api/v1/instances/{instance_id}` - Destroy an instance
- `POST /api/v1/instances/{instance_id}/start` - Start a stopped instance
- `POST /api/v1/instances/{instance_id}/stop` - Stop a running instance
- `GET /api/v1/instances/{instance_id}/ssh` - Get SSH URL for an instance
- `GET /api/v1/instances/{instance_id}/logs` - Get logs for an instance
- `PATCH /api/v1/instances/{instance_id}/bid` - Change bid price for an instance
- `PATCH /api/v1/instances/{instance_id}/label` - Label an instance
- `GET /api/v1/search/instances` - Search through your rented instances
- `GET /api/v1/search/offers` - Search for available GPU instances to rent
- `GET /api/v1/autoscalers` - List autoscaler groups
- `POST /api/v1/autoscalers` - Create a new autoscaler group
- `PATCH /api/v1/autoscalers/{autoscaler_id}` - Update an autoscaler group
- `DELETE /api/v1/autoscalers/{autoscaler_id}` - Delete an autoscaler group

### Example API Usage

#### List Available Instances

```bash
curl -X GET "http://localhost:8000/api/v1/instances?min_gpus=1&gpu_name=RTX+3090"
```

#### Search for Available RTX 4090 Instances

```bash
curl -X GET "http://localhost:8000/api/v1/search/offers?query=gpu_name%3DRTX_4090%20num_gpus%3E%3D1"
```

#### Create a New Instance

```bash
curl -X POST "http://localhost:8000/api/v1/instances" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "nvidia/cuda:11.6.2-base-ubuntu20.04",
    "onstart": "echo hello",
    "price": 0.2,
    "disk": 32
  }'
```

## Project Structure

```
gpu-proxy/
├── src/                # Source code
│   ├── api/            # API package
│   │   ├── __init__.py
│   │   ├── models.py   # Pydantic models
│   │   └── routes.py   # API routes
│   ├── core/           # Core functionality
│   │   ├── __init__.py
│   │   └── vast_client.py  # Vast.ai SDK client
│   ├── __init__.py
│   └── main.py         # FastAPI application
├── .env.sample         # Sample environment variables
├── requirements.txt    # Python dependencies
├── run.py              # Script to run the API
└── README.md           # Project documentation
```

## Development

### Running in Debug Mode

Set `DEBUG=True` in your `.env` file to enable auto-reloading when code changes.

### Future Enhancements

- Authentication and authorization
- Rate limiting
- Caching for frequently accessed data
- WebSocket support for real-time instance monitoring
- Enhanced filtering options for instance selection
- Job scheduling and automation

## License

This project is licensed under the ISC License - see the LICENSE file for details. 