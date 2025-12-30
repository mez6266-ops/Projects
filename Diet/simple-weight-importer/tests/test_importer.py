from src.importer import import_calories_data

def test_import_calories_data():
    import_calories_data('data/sample_calories.csv', 'data/weight_history.csv')
    
    with open('data/weight_history.csv', 'r') as f:
        lines = f.readlines()
    
    assert len(lines) > 0  # Check that the file is not empty
    assert "week_start" in lines[0]  # Check that the header is present
    # Additional assertions can be added here to check for specific data entries or duplicates.