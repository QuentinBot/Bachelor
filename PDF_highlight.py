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


def extract_text(directory):
    """
    This function is for extracting the basics
    :param directory: the directory where we find the files that need extraction
    :return:
    """

    def highlight_match(text):
        """
        This function creates a new PDF file with the corresponding text passage highlighted
        :param text: the text that will be highlighted
        :return:
        """
        output_buffer = BytesIO()

        area = page.search_for(text)
        if not len(area) == 0:
            highlight = page.add_highlight_annot(area)
            highlight.update()
            print("Highlighted " + text)
        pdf.save(output_buffer)
        with open("./highlighted/" + file + "_highlighted.pdf", mode="wb") as f:
            f.write(output_buffer.getbuffer())

    def basic_pattern_match(matcher, doc, i, matches):
        """
        This function gets called once the firstMatcher found his pattern in the text.
        It then processes the match and extracts the information regarding the pollutants.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
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

        value = pol = ""
        for tok in span:
            # print(tok.text + ": " + tok.pos_ + " " + tok.dep_)
            # find the pollutant in the text
            if tok.text in pollutants_no_number:
                pol = tok.text
                if tok.nbor().text in pollutants_numbers:
                    pol += tok.nbor().text
            # check if the trend is negative or positive
            elif tok.lemma_ in negative:
                value = "-"
            # add the actual numerical value of the pollutant
            elif tok.pos_ == "NUM" and tok.nbor().dep_ == "pobj":
                # print("############################")
                # print(file)

                # check if the text contains more than just the number
                text = tok.text
                if "~" in text:
                    text = text[1:]
                if "–" in text:
                    text = text.split("–")[0]
                if "e" in text:
                    text = text.split("e")[0]
                number = float(text)
                value += str(number)

        # add the matched value to our current article data. If there is already a value stored for the pollutant, we will add it to the list
        if pol not in article_data:
            article_data[pol] = [value]
        elif value not in article_data[pol]:
            article_data[pol].append(value)
        print(doc[start:end])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

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

            # now we need to fit each page into a single line, because PyMuPdf has some problems with newlines and words that are split between lines
            page_as_line = squish_page(page.get_text().splitlines())
            doc = nlp(page_as_line)

            # testing ground
            """
            for tok in doc:
                if tok.text == "showed" and tok.nbor().text == "smaller":
                    for token in tok.sent:
                        print(token.text + ": " + token.pos_ + " " + token.dep_)
            """

            pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": "NUM"}, {"TEXT": "%"}]
            matcher.add("firstMatcher", [pattern], on_match=basic_pattern_match)
            matches = matcher(doc)

        if not link_found:
            print("no link found for " + file)
        else:
            total_data.append(article_data)
        pdf.close()

    # export the extracted data to a csv file
    df = pd.DataFrame(total_data)
    df.to_csv(r"./extracted_data.csv", index=False)
    print(df)

    not_found = []
    training_data = pd.read_csv("./training_data.csv", sep=";")
    for data in total_data:
        found = False
        for i, doi in training_data["DOI"].iteritems():
            if doi in data["DOI"] or data["DOI"] in doi:
                found = True
                break
        if not found:
            not_found.append(data["DOI"])
    # for data in total_data:
    #     print(data)
    print(not_found)


def squish_page(lines):
    """
    This function converts a page into a single line of text
    :param lines: the lines of the page as a list
    :return: the text of the page in a single line
    """

    page_text = ""
    for line in lines:
        line = line.strip()
        if line[-1:] == "-":
            page_text += line[:-1]
        else:
            page_text += line + " "
    return page_text


if __name__ == "__main__":
    # extract text from the pdf document
    extract_text("./Doc/articles/PDF/")
