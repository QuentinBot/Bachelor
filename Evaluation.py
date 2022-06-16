import pandas as pd

def main():
    training_data = pd.read_csv("./training_data.csv", sep=";")
    extracted_data = pd.read_csv("./extracted_data.csv")
    print(training_data)
    print(extracted_data)

if __name__ == "__main__":
    main()
