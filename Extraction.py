from pdfminer.high_level import extract_text
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import lxml
import spacy
from spacy import displacy
from spacy.matcher import Matcher
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
    matcher = Matcher(nlp.vocab)

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

        # these are the air pollutants that we need to take a look at
        pollutants = ["NO 2", "PM 2.5", "PM 10", "BC", "NO X", "CO", "O 3", "SO 2", "NH 3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO 3", "SO 4", "OM", "BBOA", "HOA", "OOA"]
        pollutants_no_number = ["NO", "PM", "BC", "CO", "O", "SO", "NH", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "OM", "BBOA", "HOA", "OOA"]
        divs = soup.findAll("div", xmlns="http://www.tei-c.org/ns/1.0")
        for div in divs:
            section = nlp(elem_to_text(div))
            for sent in section.sents:
                for p in pollutants:
                    if p in sent.text:
                        found_value = False
                        pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'POS': "NUM", 'OP':"?"}, {'LEMMA': "concentration", 'OP': "?"}, {"LEMMA": {"IN": ["increase", "decrease", "reduce"]}}, {"POS": "ADP"}, {"POS": "NUM"}, {"DEP": "pobj"}]
                        matcher.add("firstMatcher", [pattern])
                        matches = matcher(sent)
                        for match_id, start, end in matches:
                            print(sent[start:end])
                        for tok in sent:
                            if tok.pos_ == "NUM" or "%" in tok.text:
                                found_value = True
                            # print(tok.text, "-->", tok.dep_, "-->", tok.pos_)
                        # if found_value:
                            # print(p, " ", sent)
                            # displacy.serve(sent, style="dep")

        # finally we will add the article data to our total data
        total_data.append(article_data)
        print(article_data["Title"])
        print()
        i += 1
        # break
        if i == 20:
            break

    for data in total_data:
        print(data)
    
    print(i)


if __name__ == "__main__":
    main()
