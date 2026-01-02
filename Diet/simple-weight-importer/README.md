# Simple Weight Importer

This project is designed to import a sample calories CSV file, perform minimal editing, and append the data to a weight history CSV file without creating duplicates. It serves as a learning tool for understanding how to read and write CSV files in Python.

## Project Structure

```
simple-weight-importer
├── src
│   ├── __init__.py
│   ├── importer.py
│   └── main.py
├── data
│   ├── sample_calories.csv
│   └── weight_history.csv
├── tests
│   └── test_importer.py
├── README.md
├── requirements.txt
└── pyproject.toml
```

## Getting Started

### Prerequisites

Make sure you have Python installed on your machine. You can download it from [python.org](https://www.python.org/downloads/).

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd simple-weight-importer
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Usage

To run the importer, execute the following command:
```
python src/main.py
```

This will read the `sample_calories.csv` file, process the data, and append it to the `weight_history.csv` file without creating duplicates.

### Running Tests

To ensure that the import functionality works correctly, you can run the tests located in the `tests` directory:
```
python -m unittest discover -s tests
```

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request with your changes.

## License
# test commit

This project is licensed under the MIT License. See the LICENSE file for more details.