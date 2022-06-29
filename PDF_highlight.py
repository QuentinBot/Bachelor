import fitz
import sys
import os
from pprint import pprint
from io import BytesIO
import pandas as pd
from spacy.matcher import Matcher
import spacy


pollutants_no_number = ["NO", "PM", "BC", "CO", "O", "SO", "NH", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "OM", "BBOA", "HOA", "OOA", "PMPM", "NO2", "PM2.5", "PM10", "NOX", "O3", "SO2", "NH3", "NO3", "SO4"]
pollutants_numbers = ["2", "2.5", "10", "X", "3", "4"]

negative = ["decrease", "reduce", "drop", "decline", "plummet", "reduction"]
positive = ["increase"]
trend = negative + positive


def basic_pattern_match(matcher, doc, i, matches):
    match_id, start, end = matches[i]

    # this is the extracted passage in the text
    span = doc[start:end]
    print(span)


def extract_text(directory):

    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # this is where we will store all the extracted data
    total_data = []

    # get the files in the directory and iterate over them
    directories = os.listdir(directory)
    directories.sort()
    for file in directories:
        # this is for storing the data of each file
        article_data = {}

        pdf = fitz.open(directory+file)
        link_found = False

        # let's go over page after page
        for pg in range(len(pdf)):
            page = pdf[pg]

            # we need to find the doi, for better evaluation purposes
            if not link_found:
                # checks the links if there is a link to doi.org
                links = page.get_links()
                for link in links:
                    if "uri" in link and "doi.org" in link["uri"]:
                        link_found = True
                        article_data["DOI"] = link["uri"]
                        break

                if not link_found:
                    # or check the lines if there is anything looking like a doi
                    lines = page.get_text().splitlines()
                    for line in lines:
                        line = line.strip()
                        if "doi.org" in line or "doi: " in line.lower():
                            link_found = True
                            line = line.split()
                            for word in line:
                                if "10." in word:
                                    article_data["DOI"] = word
                            break

            doc = nlp(page.get_text())

            pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": "NUM"}, {"TEXT": "%"}]
            matcher.add("firstMatcher", [pattern], on_match=basic_pattern_match)
            matches = matcher(doc)

        if not link_found:
            print("no link found for " + file)
        else:
            total_data.append(article_data)
        pdf.close()
        break

    not_found = []
    training_data = pd.read_csv("./training_data.csv", sep=";")
    for data in total_data:
        found = False
        for i, doi in training_data["DOI"].iteritems():
            if doi in data["DOI"]:
                found = True
                break
        if not found:
            not_found.append(data["DOI"])
    # for data in total_data:
    #     print(data)
    print(not_found)

    output_buffer = BytesIO()
    for file in directories:
        pdf = fitz.open(directory+file)
        for pg in range(len(pdf)):
            page = pdf[pg]
            area = page.search_for("NO2 concentrations decreased by 34.1%")
            if not len(area) == 0:
                highlight = page.add_highlight_annot(area)
                highlight.update()
        pdf.save(output_buffer)
        pdf.close()
        with open("./highlighted/" + file + "_highlighted.pdf", mode="wb") as f:
            f.write(output_buffer.getbuffer())
        break


if __name__ == "__main__":
    # extract text from the pdf document
    extract_text("./Doc/articles/PDF/")
