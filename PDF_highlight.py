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

    def find_value(span):

        pol = ""
        up = False
        down = True
        for tok in span:
            # print(tok.text + " --> " + tok.pos_ + " -> " + tok.dep_)
            if tok.text in pollutants_no_number:
                pol = tok.text
            # check if the trend is negative or positive
            elif tok.lemma_ in negative or tok.text[0] == "-":
                down = True
            elif tok.lemma_ in positive or tok.text[0] == "+":
                down = False
            # add the actual numerical value of the pollutant
            elif (tok.pos_ == "NUM" or tok.pos_ == "X") and tok.nbor().text == "%":
                # print("############################")
                # print(file)

                # check if the text contains more than just the number
                text = tok.text
                if "~" in text or text[0] in ["−", "+"]:
                    text = text[1:]
                if "–" in text:
                    text = text.split("–")[0]
                if "e" in text:
                    text = text.split("e")[0]
                number = float(text)
                value = str(number)
                if down:
                    value = "-" + value

                # add the matched value to our current article data. If there is already a value stored for the pollutant, we will add it to the list
                if pol not in article_data:
                    article_data[pol] = [value]
                elif value not in article_data[pol]:
                    article_data[pol].append(value)

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

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

        find_value(span)

    def no_pollutant_match(matcher, doc, i, matches):
        """
        This function gets called once the no_poll_matcher found his pattern in the text.
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

        # get the previous sentence to find the pollutant
        prev_sent = ""
        first_token = span[0]
        index = first_token.i
        for k in reversed(range(index)):
            token = doc[k]
            if token.is_sent_end:
                prev_sent = token.sent
                break

        # check if there was a pollutant in the previous sentence
        pol = get_pollutant(prev_sent)
        if pol == "":
            return
        # and get the values for the pollutant in the current sentence
        values = get_values(span)
        # add the matched value to our current article data. If there is already a value stored for the pollutant, we will add it to the list
        if pol not in article_data:
            article_data[pol] = values
        else:
            for value in values:
                if value not in article_data[pol]:
                    article_data[pol].append(value)

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def bracket_matcher(matcher, doc, i, matches):
        match_id, start, end = matches[i]

        # this is the extracted passage in the text
        span = doc[start:end]

        # get pollutant
        pol = get_pollutant(span)
        # get values
        values = get_values(span)

        # add the matched value to our current article data. If there is already a value stored for the pollutant, we will add it to the list
        if pol not in article_data:
            article_data[pol] = values
        else:
            for value in values:
                if value not in article_data[pol]:
                    article_data[pol].append(value)

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # these are the patterns which we are looking for
    pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": "NUM"}, {"TEXT": "%"}]
    long_pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": "NUM"}, {"TEXT": "%"}, {"TEXT": "at", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"OP": "?"}, {"TEXT": "site", "OP": "?"}, {"TEXT": {"IN": [",", "and"]}}, {"POS": "NUM"}, {"TEXT": "%"}, {"TEXT": "at", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"OP": "?"}, {"TEXT": "site", "OP": "?"}, {"TEXT": {"IN": [",", "and"]}}, {"POS": "NUM"}, {"TEXT": "%"}]
    two_pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"POS": {"IN": ["NUM", "X"]}}, {"TEXT": "%"}, {"TEXT": "and"}, {"POS": "NUM"}, {"TEXT": "%"}]
    no_pollutant_pattern = [{"POS": "NUM"}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"TEXT": "in"}, {"TEXT": "concentration"}, {"LEMMA": "be"}, {"LEMMA": "record"}, {"TEXT": ","}, {"TEXT": "while"}, {"TEXT": "a"}, {"POS": "NUM"}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"LEMMA": "be"}, {"LEMMA": "observe"}, {"TEXT": "at"}, {"TEXT": "the"}, {"OP": "?"}, {"TEXT": "site"}]
    bracket_pattern = [{"LEMMA": "concentration", "OP": "?"}, {"TEXT": "of", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "markedly", "OP": "?"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"TEXT": "("},  {"POS": {"IN": ["NUM", "NOUN", "ADJ"]}}, {"TEXT": "and"}, {"POS": {"IN": ["NUM", "NOUN", "ADJ"]}}]
    matcher.add("firstMatcher", [pattern, long_pattern, two_pattern], on_match=basic_pattern_match)
    matcher.add("no_poll_matcher", [no_pollutant_pattern], on_match=no_pollutant_match)
    matcher.add("bracket_matcher", [bracket_pattern], on_match=bracket_matcher)

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
            page_as_line = squish_page(page)
            doc = nlp(page_as_line)

            # testing ground
            """
            for tok in doc:
                if tok.text == "markedly" and tok.nbor().text == "increased":
                    for t in tok.sent:
                        print(t.text + " -> " + t.pos_ + " -> " + t.dep_)
            """

            matches = matcher(doc)

        if not link_found:
            print("no link found for " + file)
        else:
            total_data.append(article_data)
        pdf.close()
        # break

    # export the extracted data to a csv file
    df = pd.DataFrame(total_data)
    df.to_csv(r"./extracted_data.csv", index=False)
    print(df)

    # this is for listing which DOI was not found
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


def squish_page(page):
    """
    This function converts a page into a single line of text
    :param page: the page object that is currently processed
    :return: the text of the page in a single line
    """
    lines = page.get_text().splitlines()
    page_text = ""
    for line in lines:
        line = line.strip()
        if line[-1:] == "-":
            page_text += line[:-1]
        else:
            page_text += line + " "
    return page_text


def get_pollutant(sent):
    """
    This function searches a sentence for a pollutant
    :param sent: the sentence that should be searched
    :return: the pollutant, or an empty string if none was found
    """
    for tok in sent:
        if tok.text in pollutants_no_number:
            return tok.text
    return ""


def get_values(sent):
    """
    This function searches a sentence for values corresponding to pollutants
    :param sent: the sentence that should be searched
    :return: a list of values for the pollutant
    """

    values = []
    down = True
    for tok in sent:
        # print(tok.text + " --> " + tok.pos_ + " -> " + tok.dep_)
        if tok.lemma_ in negative or tok.text[0] == "-":
            down = True
        elif tok.lemma_ in positive or tok.text[0] == "+":
            down = False
        # add the actual numerical value of the pollutant
        elif tok.pos_ == "NUM" and tok.nbor().text == "%":
            # check if the text contains more than just the number
            text = tok.text
            if "~" in text or text[0] in ["−", "+"]:
                text = text[1:]
            if "–" in text:
                text = text.split("–")[0]
            if "e" in text:
                text = text.split("e")[0]
            number = float(text)
            current_value = str(number)
            if down:
                current_value = "-" + current_value
            values.append(current_value)
    return values


if __name__ == "__main__":
    # extract text from the pdf document
    extract_text("./Doc/articles/PDF/")
