import fitz
import sys
import os
from pprint import pprint
import pandas as pd


def extract_text(dir):
    total_data = []

    directories = os.listdir(dir)
    directories.sort()
    for file in directories:
        article_data = {}
        pdf = fitz.open(dir+file)
        link_found = False
        for pg in range(len(pdf)):
            page = pdf[pg]

            lines = page.get_text().splitlines()
            for line in lines:
                line = line.strip()
                if "doi.org" in line or "doi: " in line.lower():
                    # print(line)
                    link_found = True
                    article_data["DOI"] = line
                    break                    
            if link_found:
                break
            links = page.get_links()
            for link in links:
                if "uri" in link and "doi.org" in link["uri"]:
                    link_found = True
                    article_data["DOI"] = link["uri"]
                    break
            if link_found:
                break
            
        if not link_found:
            print("no link found for " + file)
        else:
            total_data.append(article_data)

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

    print(not_found)

    for file in directories:
        pdf = fitz.open(dir+file)
        for pg in range(len(pdf)):
            page = pdf[pg]
            area = page.search_for("decreased by 34.1%")
            if not len(area) == 0:
                highlight = page.add_highlight_annot(area)
                highlight.update()
        break
                     
                


if __name__ == "__main__":
    # extract text from the pdf document
    extract_text("./Doc/articles/PDF/")