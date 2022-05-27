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
        soup = BeautifulSoup(f, "lxml-xml")
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

    # tool for deeper language processing, maybe not needed
    # nlp = spacy.load("en_core_web_sm")

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
        first_author = soup.find("author").persName
        if first_author:
            firstname = elem_to_text(first_author.find("forename", type="first"))
            surname = elem_to_text(first_author.find("surname"))
            article_data["FirstAuthor"] = surname + ", " + firstname
        else:
            article_data["FirstAuthor"] = "-"

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
        # break
        if i == 1000:
            break

    for data in total_data:
        print(data)
    
    print(i)


if __name__ == "__main__":
    main()
