from pdfminer.high_level import extract_text
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span
import os


def main():

    path = "Doc/articles"
    directories = os.listdir(path)
    nlp = spacy.load("en_core_web_sm")

    total_data = []
    i = 0
    for file in directories:
        article_data = {}
        pdf = extract_text("Doc/articles/" + file)
        print(file)
        doc = nlp(pdf)
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
            # elif no_region and

        total_data.append(article_data)
        i += 1
        # break
        if i == 10:
            break

    for data in total_data:
        print(data)


if __name__ == "__main__":
    main()
