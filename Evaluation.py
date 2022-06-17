import numpy as np
import pandas as pd

def main():
    # read in our training and extracted datasets
    training_data = pd.read_csv("./training_data.csv", sep=";")
    extracted_data = pd.read_csv("./extracted_data.csv")

    # rename the interesting columns
    training_data.rename(columns = {"NO2_prcnt_change":"NO2", "NOX_prcnt_change":"NOX", "CO_prcnt_change":"CO", "PM25_prcnt_change":"PM2.5", "PM10_prcnt_change":"PM10", "O3_prcnt_change":"O3", "SO2_prcnt_change":"SO2", "NH3_prcnt_change":"NH3", "NMVOCS_prcnt_change":"NMVOCS", "AOD_prcnt_change":"AOD", "BC_prcnt_change":"BC", "AQI_prcnt_change":"AQI", "BCFF_prcnt_change":"BCFF", "BCWB_prcnt_change":"BCWB", "NO3_prcnt_change":"NO3", "SO4_prcnt_change":"SO4", "OM_prcnt_change":"OM", "PM1_prcnt_change":"PM1", "BBOA_prcnt_change":"BBOA", "HOA_prcnt_change":"HOA", "OOA_prcnt_change":"OOA"}, inplace = True)

    # we currently only take a look at the percentages
    # interesting_columns = ["NO2_prcnt_change", "NOX_prcnt_change", "CO_prcnt_change", "PM25_prcnt_change", "PM10_prcnt_change", "O3_prcnt_change", "SO2_prcnt_change", "NH3_prcnt_change", "NMVOCS_prcnt_change", "AOD_prcnt_change", "BC_prcnt_change", "AQI_prcnt_change", "BCFF_prcnt_change", "BCWB_prcnt_change", "NO3_prcnt_change", "SO4_prcnt_change", "OM_prcnt_change", "PM1_prcnt_change", "BBOA_prcnt_change", "HOA_prcnt_change", "OOA_prcnt_change"]
    pollutants = ["NO2", "PM2.5", "PM10", "BC", "NOX", "CO", "O3", "SO2", "NH3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO3", "SO4", "OM", "BBOA", "HOA", "OOA", "PM1"]
    
    # count the total amount of data points in the training data to be able to calculate the recall value
    total_amount = 0
    for i in range(training_data.shape[0]):        
        for column in pollutants:
            if not pd.isna(training_data[column][i]):
                total_amount += 1

    extracted_counter = 0
    correctly_extracted = 0
    for index, doi in extracted_data["DOI"].iteritems():
        # flag for making sure the doi was found
        doi_found = False
        # flags for making sure the pollutans where found, needed if checking for multiple rows
        # no2 = nox = co = pm25 = pm10 = so2 = nh3 = nmvocs = aod = bc = aqi = bcff = bcwb = no3 = so4 = om = pm1 = bboa = hoa = ooa = True

        for index_2, doi_2 in training_data["DOI"].iteritems():
            if doi.lower() == doi_2.lower():
                doi_found = True
                i += 1
                # print("DOI found!")
                extracted_row = extracted_data.loc[index]
                training_row = training_data.loc[index_2]
                for p in pollutants:
                    if p in extracted_data.columns and not pd.isna(extracted_row[p]):
                        extracted_counter += 1
                        if training_row[p] == extracted_row[p]:
                            correctly_extracted += 1
                            # print(p + ": " + str(extracted_row[p]))

                # we use this break to not checkfor multiple lines. This is not very accurate, but easier for now
                break 

        if not doi_found:
            print(doi + " not found...")
    
    recall = round(correctly_extracted / total_amount * 100, 2)
    precision = round(correctly_extracted / extracted_counter * 100, 2)
    print("Recall: " + str(recall) + "%")
    print("Precision: " + str(precision) + "%")


if __name__ == "__main__":
    main()
