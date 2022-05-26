from pdfminer.high_level import extract_text
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import lxml
import spacy
import os


def read_tei(tei_file):
    with open(tei_file, "r") as tei:
        soup = BeautifulSoup(tei, "lxml-xml")
        return soup
    raise RuntimeError("Cannot generate a soup from the input")


def main():

    path = "Doc/articles/XML"
    directories = os.listdir(path)
    # nlp = spacy.load("en_core_web_sm")

    total_data = []
    i = 0
    for file in directories:
        article_data = {}
        soup = read_tei(path + "/" + file)

        article_data["Title"] = soup.title.getText()
        article_data["DOI"] = soup.find("idno", type="DOI").getText()
        first_author = soup.analytic.find("author").persName
        firstname = first_author.find("forename", type="first").getText()
        surname = first_author.find("surname").getText()
        article_data["FirstAuthor"] = surname + ", " + firstname

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

        total_data.append(article_data)
        i += 1
        break
        if i == 10:
            break

    for data in total_data:
        print(data)


if __name__ == "__main__":
    main()
