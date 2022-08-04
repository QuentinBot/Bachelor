import numpy as np
import pandas as pd
import sys

# all available pollutants
pollutants = ["NO2", "PM25", "PM10", "BC", "NOX", "CO", "O3", "SO2", "NH3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO3", "SO4", "OM", "BBOA", "HOA", "OOA", "PM1"]
  

# function for converting back strings that used to be lists, for a better analysis
def convert_to_list(data, columns):
    """
    This function converts back strings that used to be lists.
    For further analysis, working with lists is much easier than working with strings.
    :param data: a panda dataframe containing the data as strings
    :param columns: the column names of the data
    :return: a tuple of the panda dataframe (now containing lists instead of strings), combined with the total number of extracted values 
    """
    counter = 0
    for c in columns:
        for r in range(data.shape[0]):
            if not pd.isna(data[c][r]):
                list = []
                reading = False
                current_value = ""
                for char in data[c][r]:
                    if char == "'":
                        if reading:
                            list.append(current_value)
                            current_value = ""
                            counter += 1
                        reading = not reading
                    elif reading:
                        current_value += char
                data[c][r] = list        
    return data, counter


def main():
    # read in our training and extracted datasets
    training_data = pd.read_csv("./training_data.csv", sep=";")
    extracted_data = pd.read_csv("./extracted_data.csv")

    # rename the interesting columns
    training_data.rename(columns = {"NO2_prcnt_change":"NO2", "NOX_prcnt_change":"NOX", "CO_prcnt_change":"CO", "PM25_prcnt_change":"PM25", "PM10_prcnt_change":"PM10", "O3_prcnt_change":"O3", "SO2_prcnt_change":"SO2", "NH3_prcnt_change":"NH3", "NMVOCS_prcnt_change":"NMVOCS", "AOD_prcnt_change":"AOD", "BC_prcnt_change":"BC", "AQI_prcnt_change":"AQI", "BCFF_prcnt_change":"BCFF", "BCWB_prcnt_change":"BCWB", "NO3_prcnt_change":"NO3", "SO4_prcnt_change":"SO4", "OM_prcnt_change":"OM", "PM1_prcnt_change":"PM1", "BBOA_prcnt_change":"BBOA", "HOA_prcnt_change":"HOA", "OOA_prcnt_change":"OOA"}, inplace = True)   

    # get the needed pollutants
    needed_pollutants = get_needed_pollutants(extracted_data)

    # count the total amount of data points in the training data to be able to calculate the recall value, we only count the columns regarding percent change
    total_amount = get_total_data(training_data)

    # convert long string back to lists in the extracted data, also return amount of extracted data
    extracted_data, extracted_counter = convert_to_list(extracted_data, needed_pollutants)

    # find amount of correctly extracted data
    correctly_extracted = get_correctly_extracted(extracted_data, training_data, needed_pollutants)
    
    # calculate precision and recall
    calculate_score(extracted_counter, total_amount, correctly_extracted)


def eval_training():
    # read in our training and extracted datasets
    training_data = pd.read_csv("./only_training.csv", sep=";")
    extracted_data = pd.read_csv("./extracted_data.csv")
    
    # rename the interesting columns
    training_data.rename(columns = {"NO2_prcnt_change":"NO2", "NOX_prcnt_change":"NOX", "CO_prcnt_change":"CO", "PM25_prcnt_change":"PM25", "PM10_prcnt_change":"PM10", "O3_prcnt_change":"O3", "SO2_prcnt_change":"SO2", "NH3_prcnt_change":"NH3", "NMVOCS_prcnt_change":"NMVOCS", "AOD_prcnt_change":"AOD", "BC_prcnt_change":"BC", "AQI_prcnt_change":"AQI", "BCFF_prcnt_change":"BCFF", "BCWB_prcnt_change":"BCWB", "NO3_prcnt_change":"NO3", "SO4_prcnt_change":"SO4", "OM_prcnt_change":"OM", "PM1_prcnt_change":"PM1", "BBOA_prcnt_change":"BBOA", "HOA_prcnt_change":"HOA", "OOA_prcnt_change":"OOA"}, inplace = True)

    # get the needed pollutants
    needed_pollutants = get_needed_pollutants(extracted_data)

    # count the total amount of data points in the training data to be able to calculate the recall value, we only count the columns regarding percent change
    total_amount = get_total_data(training_data)

    # convert long string back to lists in the extracted data, also return amount of extracted data
    extracted_data, extracted_counter = convert_to_list(extracted_data, needed_pollutants)

    # find amount of correctly extracted data
    correctly_extracted = get_correctly_extracted(extracted_data, training_data, needed_pollutants)

    # calculate precision and recall
    calculate_score(extracted_counter, total_amount, correctly_extracted)


def eval_test():
    # read in our training and extracted datasets
    training_data = pd.read_csv("./test_data.csv", sep=";")
    extracted_data = pd.read_csv("./extracted_data.csv")

    # rename the interesting columns
    training_data.rename(columns = {"NO2_prcnt_change":"NO2", "NOX_prcnt_change":"NOX", "CO_prcnt_change":"CO", "PM25_prcnt_change":"PM25", "PM10_prcnt_change":"PM10", "O3_prcnt_change":"O3", "SO2_prcnt_change":"SO2", "NH3_prcnt_change":"NH3", "NMVOCS_prcnt_change":"NMVOCS", "AOD_prcnt_change":"AOD", "BC_prcnt_change":"BC", "AQI_prcnt_change":"AQI", "BCFF_prcnt_change":"BCFF", "BCWB_prcnt_change":"BCWB", "NO3_prcnt_change":"NO3", "SO4_prcnt_change":"SO4", "OM_prcnt_change":"OM", "PM1_prcnt_change":"PM1", "BBOA_prcnt_change":"BBOA", "HOA_prcnt_change":"HOA", "OOA_prcnt_change":"OOA"}, inplace = True)

    # get the needed pollutants
    needed_pollutants = get_needed_pollutants(extracted_data)

    # count the total amount of data points in the training data to be able to calculate the recall value, we only count the columns regarding percent change
    total_amount = get_total_data(training_data)

    # convert long string back to lists in the extracted data, also return amount of extracted data
    extracted_data, extracted_counter = convert_to_list(extracted_data, needed_pollutants)

    # find amount of correctly extracted data
    correctly_extracted = get_correctly_extracted(extracted_data, training_data, needed_pollutants)

    # calculate precision and recall
    calculate_score(extracted_counter, total_amount, correctly_extracted)


def get_needed_pollutants(extracted_data):

    # a list for the actually needed pollutants present in the extracted dataset
    needed_pollutants = []
    for p in pollutants:
        if p in extracted_data.columns:
            needed_pollutants.append(p)
    return needed_pollutants


def get_total_data(training_data):

    total_amount = 0
    for i in range(training_data.shape[0]):        
        for column in pollutants:
            if not pd.isna(training_data[column][i]):
                total_amount += 1
    return total_amount


def get_correctly_extracted(extracted_data, training_data, needed_pollutants):
    
    # counter for correctly extracted data
    correctly_extracted = 0
    
    # let's look at every extracted DOI
    for index, doi in extracted_data["DOI"].iteritems():
        
        # flag for making sure the doi was found
        doi_found = False
        
        extracted_row = extracted_data.loc[index]

        # here we find the corresponding DOI in the training dataset to start the evaluation
        for index_2, doi_2 in training_data["DOI"].iteritems():
            if doi.lower() in doi_2.lower() or doi_2.lower() in doi.lower():
                doi_found = True
                # print("DOI found!")
                training_row = training_data.loc[index_2]
                for p in needed_pollutants:
                    if type(extracted_row[p]) == list:
                        if str(training_row[p]) in extracted_row[p]:
                            correctly_extracted += 1
                            # print(p + ": " + str(extracted_row[p]))

        if not doi_found:
            print(doi + " not found...")

    return correctly_extracted


def calculate_score(extracted_counter, total_amount, correctly_extracted):

    recall = round(correctly_extracted / total_amount * 100, 2)
    precision = round(correctly_extracted / extracted_counter * 100, 2)
    print("Recall: " + str(recall) + "%")
    print("Precision: " + str(precision) + "%")


if __name__ == "__main__":
    
    if len(sys.argv) > 2:
        print("Maximum of one argument")
    elif len(sys.argv) == 2:
        if sys.argv[1] == "training":
            eval_training()
        elif sys.argv[1] == "test":
            eval_test()
        else:
            print("Argument is either test or training")
    else:
        main()
