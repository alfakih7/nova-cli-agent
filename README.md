# Nova CLI-Agent (powered by SambaNova)

Nova CLI-Agent: Your lightweight, open-source AI coding companion, powered by SambaNova. A nimble alternative for code generation, analysis, bug prediction, and learning, right in your terminal.

## Features

- **Code Generation**: Create new code files based on your descriptions
- **Bug Prediction**: Anticipate potential bugs and issues before they occur
- **Code Analysis**: Analyze files for syntax issues, potential bugs, and improvements
- **Interactive Fixes**: Get AI-powered fix suggestions and apply them with a single command
- **Refactoring Suggestions**: Get ideas to improve your code's structure and readability
- **Security Audit**: Identify potential security vulnerabilities in your code
- **Performance Optimization**: Get suggestions to make your code run faster
- **Concept Explanations**: Learn about programming concepts and language features
- **Interactive Chat**: Ask questions about your code and get beginner-friendly explanations

## Installation

### Prerequisites

- Python 3.7 or higher
- SambaNova API key (get it from [SambaNova Console](https://console.sambanova.ai/))

### Install from PyPI

```
pip install nova-cli-agent
```

### Install from Source

```
git clone https://github.com/yourusername/nova-cli-agent.git
cd nova-cli-agent
pip install -e .
```

## Usage

1. Set your SambaNova API key (recommended):

```bash
export SAMBANOVA_API_KEY=your_api_key_here
```
   Alternatively, if the environment variable is not set, `nova-cli` will prompt you to enter the API key when it starts.

2. Launch the AI coding assistant:

```bash
nova-cli
```

3. Use the available commands:

```
(nova-cli) generate python fibonacci.py   # Generate a new Python file
(nova-cli) analyze your_file.py           # Analyze an existing file
(nova-cli) predict_bugs                   # Predict potential bugs
(nova-cli) explain recursion              # Learn about programming concepts
(nova-cli) fix                            # Generate and apply a fix for errors
(nova-cli) run                            # Run the current file
(nova-cli) chat How does this code work?  # Ask a question about the code
(nova-cli) refactor                       # Get refactoring suggestions
(nova-cli) security                       # Perform a security audit
(nova-cli) optimize                       # Get performance optimization suggestions
(nova-cli) show                           # Show current file content
(nova-cli) history                        # Show your coding history
(nova-cli) help                           # See all available commands
(nova-cli) quit                           # Exit the assistant
```

## Examples

### Generating new code

```
(nova-cli) generate python sort_algorithm.py
Describe what you want to generate:
Create a Python module that implements three sorting algorithms:
1. Quick sort
2. Merge sort
3. Heap sort
Each algorithm should be implemented as a separate function with detailed comments.
Include a main function that demonstrates each algorithm on sample data.
```

### Predicting potential bugs

```
(nova-cli) analyze api_client.py
(nova-cli) predict_bugs
```

The assistant will analyze the code and identify potential bugs, edge cases, race conditions, and other issues that might occur in production.

### Learning programming concepts

```
(nova-cli) explain javascript promises
```

Get a detailed explanation of JavaScript promises, including how they work, when to use them, common mistakes, and best practices.

## License

MIT

## Acknowledgments

- SambaNova for providing the AI capabilities
- Rich library for the terminal interface

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 