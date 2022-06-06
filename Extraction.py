from pdfminer.high_level import extract_text
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import lxml
import spacy
import os


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

    # the path to the articles, all saved as tei-xml files
    path = "Doc/articles/XML"

    # get every file in the directory
    directories = os.listdir(path)
    directories.sort()

    # tool for deeper language processing, maybe not needed
    nlp = spacy.load("en_core_web_sm")

    # this array will store the data for every single article
    total_data = []
    i = 0
    for file in directories:

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


        # now let's take a look at the results section
        found_results = False
        # these are the air pollutants that we need to take a look at
        pollutants = ["NO 2", "PM 2.5", "PM 10", "BC", "NO X", "CO", "O 3", "SO 2", "NH 3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO 3", "SO 4", "OM", "PM 1", "BBOA", "HOA", "OOA"]
        divs = soup.findAll("div", xmlns="http://www.tei-c.org/ns/1.0")
        for div in divs:
            # finding the results section by looking for a part containing 'results'
            if elem_to_text(div).__contains__("Results"):
                found_results = True
            if found_results:
                section = nlp(elem_to_text(div))
                for tok in section:
                    # look for words signalling that the air quality changed
                    if "decrease" in tok.text or "increase" in tok.text or "reduc" in tok.text:
                        sentence = tok.sent.text
                        found_word = False
                        # check if the sentence contains any information regarding air pollutants
                        for word in pollutants:
                            if word in sentence:
                                found_word = True
                                print("Found " + word + " in sentence:")
                                print(sentence)
                                print()
                                break
                        # we can (hopefully) ignore these sentences, since they do not carry any useful information
                        if not found_word:
                            print("No word found in sentence:")
                            print(sentence)
                            print()

        if not found_results:
            print("No result section found...")
                        

        """
        text = extract_text("Doc/articles/" + file)
        print(file)
        doc = nlp(text)
        no_doi = True

        for e in doc.ents:
            if e.label_ == "GPE":
                article_data["region"] = e.text
                break

        for tok in doc:
            # print(tok.text, "-->", tok.dep_, "-->", tok.pos_)

            if no_doi and tok.text.__contains__("10."):
                article_data["doi"] = tok.text
                no_doi = False
        
        """

        # finally we will add the article data to our total data
        total_data.append(article_data)
        i += 1
        break
        if i == 10:
            break

    for data in total_data:
        print(data)
    
    print(i)


if __name__ == "__main__":
    main()
