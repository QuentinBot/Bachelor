from pdfminer.high_level import extract_text
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import lxml
import spacy
from spacy import displacy
from spacy.matcher import Matcher
import os
import sys


# function for reading the tei-xml file
def read_file(file):
    with open(file, "r") as f:
        soup = BeautifulSoup(f, "lxml")
        return soup
    raise RuntimeError("Could not generate soup from given inputfile")


# function for returning text of element in xml-file
def elem_to_text(elem, default="-"):
    if elem:
        return elem.getText()
    else:
        return default


def main():

    def basic_pattern_match(matcher, doc, i, matches):
        match_id, start, end = matches[i]
            
        # this is the extracted passage in the text
        span = doc[start:end]

        # these are the previous few words, to check if there are multiple pollutants in one sentence because if so, we have to ignore it
        span_previous = doc[start-3:start]
        if span_previous[2].text in ["and", ","]:
            if span_previous[1].text in pollutants_no_number or span_previous[1].text in pollutants_numbers:
                return
            if span_previous[1].text == "," and span_previous[0].text in pollutants_no_number or span_previous[0].text in pollutants_numbers:
                return
            
        value = ""
        for tok in span:
            #print(tok.lemma_)
            if tok.text in pollutants_no_number:
                if tok.text[0:int(len(tok.text)/2)] in pollutants_no_number:
                    pol = tok.text[0:int(len(tok.text)/2)]
                else:
                    pol = tok.text
                if show_sent:
                    print("------ sentence found ------")
                    print(tok.sent)
                    print("----------------------------")
                if tok.nbor().text in pollutants_numbers:
                    pol += tok.nbor().text
            # elif tok.lemma_ in positive:
            #     value = "+"
            elif tok.lemma_ in negative:
                value = "-"
            elif tok.pos_ == "NUM" and tok.nbor().dep_ == "pobj":
                value += tok.text # + tok.nbor().text
        # add the matched value to our current article data. If there is already a value stored for the pollutant, we will add it to the list
        if pol not in article_data:
            article_data[pol] = [value]
        elif value not in article_data[pol]:
            article_data[pol].append(value)
        print(doc[start:end])

    # the path to the articles, all saved as tei-xml files
    path = "Doc/articles/XML"

    # get every file in the directory
    directories = os.listdir(path)
    directories.sort()

    # tool for deeper language processing, maybe not needed
    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # this array will store the data for every single article
    total_data = []
    i = 0
    for file in directories:
        show_sent = False
        if "-sentence" in sys.argv:
            show_sent = True

        # each article has a dictionary where the information is stored
        article_data = {}
        soup = read_file(path + "/" + file)

        # now we will first try to retrieve the title, doi and the first named author
        article_data["Title"] = elem_to_text(soup.title)
        article_data["DOI"] = elem_to_text(soup.find("idno", type="DOI"))

        first_author = soup.find("author").persname
        if first_author:
            firstname = elem_to_text(first_author.find("forename", type="first"))
            middlename = elem_to_text(first_author.find("forename", type="middle"))
            if middlename != "-" :
                firstname = firstname + " " + middlename
            surname = elem_to_text(first_author.find("surname"))
            article_data["FirstAuthor"] = surname + ", " + firstname

        # find one table and create a pandas dataframe
        tables = soup.find("table")
        if tables:
            final_table = []
            for row in tables.find_all("row"):
                cols = row.find_all("cell")
                row_list = [ dat.text for dat in cols]
                if len(final_table) != 0 and len(row_list) != len(final_table[0]):
                    continue
                final_table.append(row_list)
            panda = pd.DataFrame(final_table)
            # print(panda)

        #TODO: where is CO2??
        # these are the air pollutants that we need to take a look at
        pollutants = ["NO 2", "PM 2.5", "PM 10", "BC", "NO X", "CO", "O 3", "SO 2", "NH 3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO 3", "SO 4", "OM", "BBOA", "HOA", "OOA"]
        # we need the pollutants without the numbers because otherwise they would count as two words 
        pollutants_no_number = ["NO", "PM", "BC", "CO", "O", "SO", "NH", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "OM", "BBOA", "HOA", "OOA", "PMPM", "NO2", "PM2.5", "PM10", "NOX", "O3", "SO2", "NH3", "NO3", "SO4"]
        pollutants_numbers = ["2", "2.5", "10", "X", "3", "4"]
        doc = nlp(soup.text)

        # testing ground for finding tokens and tags
        """
        for tok in doc:
            if tok.text == "17" and tok.nbor().text == "%" or tok.text == "17.9":
                print("------------------------")
                print(tok.sent)
                print("------------------------")
        """        

        negative = ["decrease", "reduce", "drop", "decline", "plummet", "reduction"]
        trend = ["increase", "decrease", "reduce", "drop", "decline", "plummet", "reduction"]

        # this is the first basic pattern to extract the pollutant's data
        pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP':"?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": "NUM"}, {"TEXT": "%"}]
        matcher.add("firstMatcher", [pattern], on_match=basic_pattern_match)   
        matches = matcher(doc)     

        # finally we will add the article data to our total data
        total_data.append(article_data)
        print(article_data["Title"])
        print()
        i += 1
        # break
        # if i == 10:
            # break

    for data in total_data:
        print(data)
    if "PM" in total_data:
        total_data.remove("PM")

    df = pd.DataFrame(total_data)
    df.to_csv(r"./extracted_data.csv", index=False)
    print(df)
    print(i)


if __name__ == "__main__":
    main()
