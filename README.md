# Vanna SQL Agent

A natural language to SQL conversion system with BigQuery execution, vector similarity learning, and a SQL approval workflow.

## ✨ Features

- **Text-to-SQL Conversion**: Transform natural language questions into SQL queries using Vanna AI
- **SQL Approval Workflow**: Review and approve SQL before execution for safety and control
- **BigQuery Integration**: Execute approved SQL against Google BigQuery
- **Vector Database**: Store and retrieve similar queries semantically for improved generation
- **Multiple Interfaces**: REST API, CLI, and React web dashboard

## 📊 Architecture

The system consists of three main components:

1. **Python Backend**: Core SQL agent, FastAPI server, and CLI
2. **React Frontend**: User-friendly web dashboard
3. **Vector Database**: ChromaDB for storing and retrieving question-SQL pairs

## 🚀 Quick Start

### Using Docker Compose

The easiest way to get started is with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/yourusername/vanna-sql-agent.git
cd vanna-sql-agent

# Create environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys and settings

# Start the services
docker-compose up -d
```

This will start both the backend API server and the frontend web dashboard.

### Manual Setup

Alternatively, you can set up the components manually:

#### Backend

```bash
cd vanna-sql-agent/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Start the API server
python main.py
```

#### Frontend

```bash
cd vanna-sql-agent/frontend

# Install dependencies
npm install

# Start development server
npm start
```

## 📖 Documentation

Detailed documentation is available for each component:

- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
- [CLI Guide](docs/cli-guide.md)
- [API Reference](docs/api-reference.md)

## 🧩 Components

### Backend (Python)

- **SQL Agent**: Core engine for text-to-SQL conversion
- **FastAPI Server**: REST API for all functionality
- **CLI**: Command-line interface for queries and administration

### Frontend (React)

- **Query Interface**: Clean UI for entering natural language questions
- **SQL Review**: Interface for reviewing and approving generated SQL
- **Results Visualization**: Display and exploration of query results
- **History Management**: Browse and reuse past queries

## 🛠️ Customization

The system is designed to be extended and customized:

- **Connect to Different Databases**: Modify the agent to support other database types
- **Custom Embedding Models**: Swap the sentence transformer model for your own
- **Additional Interfaces**: Build new interfaces using the API

## 🔍 Examples

See the `examples/` directory for sample usage, including:

- Custom agent configuration
- Sample queries for various domains
- Integration patterns

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
