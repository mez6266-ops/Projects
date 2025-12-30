def get_percentage(weight, percent):
    return weight * (percent / 100)

def main():
    try:
        max_weight = float(input("Enter your 1-rep max: "))
        percent = float(input("Enter the percentage you want (e.g., 80): "))
    except ValueError:
        print("Please enter valid numbers.")
        return

    result = get_percentage(max_weight, percent)
    print(f"{percent}% of {max_weight} is {result:.1f} lbs")

if __name__ == "__main__":
    main()