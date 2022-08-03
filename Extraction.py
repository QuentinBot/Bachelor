import fitz
import os
from io import BytesIO
import pandas as pd
from spacy.matcher import Matcher
import spacy
import re
import tabula
from spacy import displacy


no2_list = ["NO2", "AQINO2", "NO₂"]
nox_list = ["NOx", "NOX"]
co_list = ["CO"]
pm25_list = ["AQIPM2.5", "PM2:5", "PM2.5", "PM25"]
pm10_list = ["PM10"]
o3_list = ["ozone", "O3"]
so2_list = ["SO2", "BLSO2"]
nh3_list = ["NH3"]
nmvocs_list = ["S56VOCs", "NMVOCS", "VOCs", "VOC", "VOCS", "benzene"]
aod_list = ["AOD"]
bc_list = ["BC", "EC"]
aqi_list = ["AQI"]
bcff_list = ["BCFF"]
bcwb_list =["BCWB"]
no3_list = ["NO3", "nitrate"]
so4_list = ["SO4"]
om_list = ["OM"]
pm1_list = ["PM1"]
bboa_list = ["BBOA"]
hoa_list = ["HOA"]
ooa_list = ["OOA"]
pollutants_no_number = ["OC", "CO2", "NO", "PM", "O", "SO", "NH"] + no2_list + nox_list + co_list + pm25_list + pm10_list + o3_list + so2_list + nh3_list + nmvocs_list + aod_list + bc_list + aqi_list + bcff_list + bcwb_list + no3_list + so4_list + om_list + pm1_list + bboa_list + hoa_list + ooa_list
pollutants_numbers = ["2", "2.5", "10", "X", "3", "4"]
actual_pollutants = ["NO2", "PM2.5", "PM10", "BC", "NOX", "CO", "O3", "SO2", "NH3", "NMVOCS", "AOD", "AQI", "BCFF", "BCWB", "NO3", "SO4", "OM", "BBOA", "HOA", "OOA", "PM1"]

negative = ["decrease", "reduce", "drop", "decline", "plummet", "reduction", "lower", "-", "low", "negative", "improve", "enhancement", "halve", "diminish", "fall", "down"]
positive = ["+", "increase", "positive", "rise"]
trend = negative + positive
number_regex = "[-,−,+,~]?[0-9]+,?[0-9]*[–,–,−]?[0-9]*,?[0-9]*"
trend_number_regex = "[-,−,+,~]{1}[0-9]+,?[0-9]*[–,–,−]?[0-9]*,?[0-9]*"
highlighted_sentences = []


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
        # check if already highlighted
        if text in highlighted_sentences:
            return

        output_buffer = BytesIO()

        area = page.search_for(text)
        if not len(area) == 0:
            highlight = page.add_highlight_annot(area)
            highlight.update()
            print("Highlighted " + text)
            highlighted_sentences.append(text)
        pdf.save(output_buffer)
        with open("./highlighted/" + file + "_highlighted.pdf", mode="wb") as f:
            f.write(output_buffer.getbuffer())

    def no_pollutant_match(matcher, doc, i, matches):
        """
        This function gets called once the no_poll_matcher found its pattern in the text.
        It then processes the match and extracts the information regarding the pollutants.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
        print("called no pollutant matcher")
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
        pols = get_all_pollutants(prev_sent)
        if not pols:
            if type(prev_sent) == str:
                return
            # look at the previous sentence
            first_token = prev_sent[0]
            index = first_token.i
            for k in reversed(range(index)):
                token = doc[k]
                if token.is_sent_end:
                    prev_sent = token.sent
                    break
            pols = get_all_pollutants(prev_sent)
            if not pols:
                return
        pol = pols[-1]
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
        """
        This function gets called once the bracket_matcher found its pattern in the text.
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
        # print("called bracket matcher with " + span.text)
        # displacy.serve(span)
        # these are the previous few words, to check if there are multiple pollutants in one sentence because if so, we have to ignore it
        span_previous = doc[start-3:start]
        if len(span_previous) > 2:
            if span_previous[2].text in ["and", ","]:
                if span_previous[1].text in pollutants_no_number or span_previous[1].text in pollutants_numbers:
                    return
                if span_previous[1].text == "," and span_previous[0].text in pollutants_no_number or span_previous[0].text in pollutants_numbers:
                    return

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

    def multi_matcher(matcher, doc, i, matches):
        """
        This function gets called once the multi_matcher found its pattern in the text.
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

        # get the pollutants and values
        pollutants = get_all_pollutants(span)
        values = get_values(span)
        double = False
        # print("called multimatcher")
        if 2*len(pollutants) == len(values):
            double = True
        # ignore if not same amount of pollutants and values
        elif len(pollutants) == 1 or len(pollutants) != len(values):
            return

        # print("##############")
        # print(span.text)
        # print(matcher)
        # print(pollutants)
        # print(values)
        # relate each pollutant to a value and add it to our current article data

        # relate each pollutant to its values
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = [values[j]]
            elif values[j] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j])
            if double:
                if values[j+len(pollutants)] not in article_data[current_pollutant]:
                    article_data[current_pollutant].append(values[j+len(pollutants)])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def plus_minus_matcher(matcher, doc, i, matches):
        """
        This function get called once the plus_minus_matcher finds its pattern in the text.
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

        # get pollutants and values
        pollutants = get_all_pollutants(span)
        values = get_plus_minus_values(span)

        # relate each pollutant to its value
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = [values[j]]
            elif values[j] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def no_trend_matcher(matcher, doc, i, matches):
        """
        This function gets called once the long_no_trend_matcher found its pattern in the text.
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

        # get pollutants and values
        pollutants = get_all_pollutants(span)
        values = get_no_trend_values(span)
        double = False

        # check if there are two values for one pollutant
        if 2*len(pollutants) == len(values):
            double = True

        # relate each pollutant to its values
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = [values[j]]
            elif values[j] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j])
            if double:
                if values[j+len(pollutants)] not in article_data[current_pollutant]:
                    article_data[current_pollutant].append(values[j+len(pollutants)])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def no_pollutant_no_trend(matcher, doc, i, matches):
        """
        This function gets called once the no_pollutant_no_trend matcher found its pattern in the text.
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
        pols = get_all_pollutants(prev_sent)
        if not pols:
            if type(prev_sent) == str:
                return
            # look at the previous sentence
            first_token = prev_sent[0]
            index = first_token.i
            for k in reversed(range(index)):
                token = doc[k]
                if token.is_sent_end:
                    prev_sent = token.sent
                    break
            pols = get_all_pollutants(prev_sent)
            if not pols:
                return

        # pollutant is the last found pollutant
        pol = pols[-1]
        # get the values
        values = get_no_trend_values(span)

        # relate the pollutant to its values
        if pol not in article_data:
            article_data[pol] = values
        else:
            for value in values:
                if value not in article_data[pol]:
                    article_data[pol].append(value)

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def no_percentage_multi_matcher(matcher, doc, i, matches):
        """
        This function gets called once the no_percentage_multi_matcher found its pattern in the text.
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

        # get pollutants and values
        pollutants = get_all_pollutants(span)
        values = get_all_values(span)

        # check if valid multi pattern
        if len(pollutants) != len(values):
            return

        # relate each pollutant to its value
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = [values[j]]
            elif values[j] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def no_percentage_bracket_matcher(matcher, doc, i, matches):
        """
        This function gets called once the no_percentage_bracket_matcher found its pattern in the text.
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

        # get pollutant and values
        pol = get_pollutant(span)
        values = get_all_values(span)

        # relate the pollutant to its values
        if pol not in article_data:
            article_data[pol] = values
        else:
            for value in values:
                if value not in article_data[pol]:
                    article_data[pol].append(value)

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def two_in_one_matcher(matcher, doc, i, matches):
        """
        This function gets called once the two_in_one_matcher found its pattern in the text.
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

        # get pollutants and values
        pollutants = get_all_pollutants(span)
        values = get_values(span)

        # check if valid two in one patter, there have to be two values for one pollutant
        if 2*len(pollutants) != len(values):
            return

        # relate each pollutant to its values
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = [values[j*2]]
                article_data[current_pollutant].append(values[j*2+1])
                continue
            if values[j*2] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j*2])
            if values[j*2+1] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(values[j*2+1])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def two_pol_one_value_matcher(matcher, doc, i, matches):
        """
        This function get called once the two_pol_one_value matcher finds its pattern in the text.
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

        # get pollutants and values
        pollutants = get_all_pollutants(span)
        value = get_values(span)

        # check if valid two pol one value pattern, there has to be exactly one value
        if len(value) != 1:
            return

        # relate each pollutant to the value
        for j in range(len(pollutants)):
            current_pollutant = pollutants[j]
            if current_pollutant not in article_data:
                article_data[current_pollutant] = value
            elif value[0] not in article_data[current_pollutant]:
                article_data[current_pollutant].append(value[0])

        # call the highlight function to highlight the pattern in the text
        highlight_match(span.sent.text)

    def table_finder(matcher, doc, i, matches):
        """
        This function gets called once the table_finder matcher found its pattern in the text.
        It then processes the match and extracts the information regarding the pollutants.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
        # check if page was already processed
        if pg+1 in pages:
            return

        match_id, start, end = matches[i]

        # this is the extracted passage in the text
        span = doc[start:end]

        # get the pollutant
        pollutant = get_pollutant(span)
        print(pollutant)

        # extract the tables on the current page
        df = tabula.read_pdf(directory + file, pages=pg+1)
        for d in df:
            values = []
            print("##########################")
            interesting_row = -1

            # find the row that contains the percentage numbers
            for idx, row in d.iloc[:, :1].iterrows():
                if "percent change" in str(row[0]).lower():
                    interesting_row = idx
            if interesting_row != -1:

                # get the values from the row
                for v in d.iloc[interesting_row]:
                    try:
                        neg = False
                        v = str(v)
                        if v == "nan":
                            continue
                        if v[0] in ["-", "−"]:
                            v = v[1:]
                            neg = True
                        v = float(v)
                        if neg:
                            v = "-" + str(v)
                        values.append(v)
                    except ValueError:
                        print(str(v) + " not a value")

                # relate the pollutant to its values
                if pollutant not in article_data:
                    article_data[pollutant] = values
                else:
                    for v in values:
                        if v not in article_data[pollutant]:
                            article_data[pollutant].append(v)

                # call the highlight function to highlight the pattern in the text
                highlight_match(span.sent.text)

        # mark page as processed
        pages.append(pg+1)

    def different_pol_table(matcher, doc, i, matches):
        """
        This function gets called once the different_pol_table matcher found its pattern in the text.
        It then processes the match and extracts the information regarding the pollutants.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
        # check if page was already processed
        if pg+1 in pages:
            return

        match_id, start, end = matches[i]

        # this is the extracted passage in the text
        span = doc[start:end]

        # extract the tables on the current page
        df = tabula.read_pdf(directory + file, pages=pg+1)
        for d in df:
            print("########################")
            current_pol = "NO POLLUTANT"
            # the column name corresponds to a pollutant here, so we mainly need to get the values
            for name, values_table in d.iteritems():
                # get the pollutant of the column
                current_name = fix_pollutant(name.replace("Country ", ""))
                if current_name in pollutants_no_number:
                    current_pol = current_name
                print(current_pol)
                values = []
                # get the values in the column
                for v in values_table:
                    v = str(v)
                    v = v.split()[-1]
                    try:
                        neg = False
                        v = str(v)
                        if v == "nan":
                            continue
                        if v[0] in ["-", "−"]:
                            v = v[1:]
                            neg = True
                        v = float(v)
                        if neg:
                            v = "-" + str(v)
                        values.append(v)
                    except ValueError:
                        print(str(v) + " not a value")

                # relate the pollutant to its values
                if current_pol not in article_data:
                    article_data[current_pol] = values
                else:
                    for v in values:
                        if v not in article_data[current_pol]:
                            article_data[current_pol].append(v)

        highlight_match(span.sent.text)
        pages.append(pg+1)

    def huge_layout_fail_table(matcher, doc, i, matches):
        """
        This function gets called once the weird_layout matcher found its pattern in the text.
        It then processes the match and extracts the information regarding the pollutants.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
        # check if page was already processed
        if pg+1 in pages:
            return

        match_id, start, end = matches[i]

        # this is the extracted passage in the text
        span = doc[start:end]

        # extract the tables on the current page
        df = tabula.read_pdf(directory + file, pages=pg+1)
        for d in df:
            print("########################")
            current_pol = "NO POLLUTANT"
            # this time, the pollutant is not at the top of the column
            for name, values_table in d.iteritems():
                values = []
                # get the pollutant and the values of the column
                for v in values_table:
                    v = fix_pollutant(str(v))
                    if v in pollutants_no_number:
                        current_pol = v
                        continue
                    v = v.split()[0]
                    try:
                        neg = False
                        if v == "nan":
                            continue
                        if v[0] in ["-", "−"]:
                            v = v[1:]
                            neg = True
                        v = float(v)
                        if neg:
                            v = "-" + str(v)
                        values.append(v)
                    except ValueError:
                        print(str(v) + " not a value")

                # relate the pollutant to its values
                if current_pol not in article_data:
                    article_data[current_pol] = values
                else:
                    for v in values:
                        if v not in article_data[current_pol]:
                            article_data[current_pol].append(v)

        highlight_match(span.sent.text)
        pages.append(pg+1)

    def table_highlighter(matcher, doc, i, matches):
        """
        This function gets called once the table_highlighter matcher found its pattern in the text.
        It then highlights the sentence that contains the match.
        :param matcher: the matcher which invoked this function
        :param doc: the document on which it searched
        :param i: the position of the current match
        :param matches: the total list of matches
        :return:
        """
        match_id, start, end = matches[i]

        # this is the extracted passage in the text
        span = doc[start:end]

        # check if it's the start of the sentence, otherwise it won't be a caption
        if not span[0].is_sent_start:
            return

        # print("#####################################################################################################")
        # print("highlighted a caption")
        # print(span.text)

        # print("#####################################################################################################")
        highlight_match(span.sent.text)

    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # these are the patterns we are looking for

    # #### NORMAL PATTERNS #### #
    # NO2 concentrations were REDUCED by 24%
    pattern = [{"TEXT": "(", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": {"IN": ["average", "mean", "also", "level", "have", "be", ",", "overall", "undergo", "show"]}, "OP": "?"}, {"TEXT": {"IN": ["of", "column", "a", "found", "which", "almost", "a", "also", "the"]}, "OP": "?"}, {'LEMMA': {"IN": ["exhibit", "concentration", "emission", "over", "the", "significant", "to", "mainly", "more", "be", "large"]}, 'OP': "?"}, {"POS": "PUNCT", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"POS": "NOUN", "OP": "?"}, {"POS": "PUNCT", "OP": "?"}, {"LEMMA": {"IN": ["entire", "in", "be", "emit", "mark"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"TEXT": {"IN": ["interval", "signiﬁcantly", ",", "all", "a", "from", "rather"]}, "OP": "?"}, {"LEMMA": {"IN": ["have", "be", "show", "station", "include", "power", "than"]}, "OP": "?"}, {"POS": "VERB", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"TEXT": {"IN": ["non", "the", "plants"]}, "OP": "?"}, {"TEXT": {"IN": ["-", "prelockdown", ","]}, "OP": "?"}, {"LEMMA": {"IN": ["significant", "and", "show"]}, "OP": "?"}, {"TEXT": "lockdown", "OP": "?"}, {"TEXT": "periods", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "i.e.", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": {"IN": ["/", "–"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "2020", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": {"IN": ["significant", "small", ",", "(", "a"]}, "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": [",", "the", "at", "trend", "(", "from"]}, "OP": "?"}, {"TEXT": {"IN": ["�", "p", "both", "the"]}, "OP": "?"}, {"TEXT": "<", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "only", "OP": "?"}, {"TEXT": {"IN": ["period", "types"]}, "OP": "?"}, {"TEXT": "of", "OP": "?"}, {"TEXT": {"IN": ["CTRL", "station"]}, "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": {"REGEX": "S[1-9]b"}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"TEXT": "2020", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": "its", "OP": "?"}, {"TEXT": "concentration", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"TEXT": {"IN": ["by", "of", "the", "(", "to"]}, "OP": "?"}, {"TEXT": {"IN": ["as", "an"]}, "OP": "?"}, {"TEXT": {"IN": ["approximately", "about", "selected", "around", "(", "approx.", "average", "TL", "PL", "much"]}, "OP": "?"}, {"TEXT": "cities", "OP": "?"}, {"LEMMA": "show", "OP": "?"}, {"TEXT": {"IN": ["up", "in", "ACV", "of", "phase", "as"]}, "OP": "?"}, {"TEXT": {"IN": ["to", "Table", "=", "("]}, "OP": "?"}, {"TEXT": "S1", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"TEXT": "�", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    long_pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "up", "OP": "?"}, {"TEXT": {"IN": ["by", "of", "to"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": ["in", "at"]}, "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "site", "OP": "?"}, {"TEXT": {"IN": [",", "and"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": ["in", "at"]}, "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "site", "OP": "?"}, {"TEXT": {"IN": [",", "and"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": "respectively", "OP": "!"}]
    two_pattern = [{"TEXT": {"IN": pollutants_no_number}}, {'TEXT': {"IN": pollutants_numbers}, 'OP': "?"}, {"LEMMA": {"IN": ["average", "mean"]}, "OP": "?"}, {'LEMMA': {"IN": ["concentration", "emission"]}, 'OP': "?"}, {"LEMMA": {"IN": ["have", "be", "show"]}, "OP": "?"}, {"LEMMA": "small", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["by", "of"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "respectively", "OP": "!"}]

    # #### NO POLLUTANT PATTERNS #### #
    # 20.2%, 30.1%, and 33% lower than those of during January
    no_pollutant_pattern = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"TEXT": "than"}, {"TEXT": {"IN": ["that", "those"]}}, {"TEXT": {"IN": ["from", "of"]}}, {"TEXT": "during", "OP": "?"}, {"POS": "PROPN"}]
    # reduction of 31 μg/m3 (63% reduction)
    pattern_l = [{"LEMMA": {"IN": trend}}, {"LEMMA": "be", "OP": "?"}, {"TEXT": "of"}, {"TEXT": "approximately", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "μg"}, {"TEXT": "/"}, {"TEXT": "m3"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"TEXT": ")"}]
    # decrease ratio over 20% including Tianjin (20%), Hebei (29%), Shanxi (24%), Shanghai (21%), Jiangsu (31%), Zhejiang (22%), Anhui (30%), Shandong (29%), Henan (33%), Hubei (23%), Shaanxi (22%), and Qinghai (22%)
    pattern_c = [{"LEMMA": {"IN": trend}}, {"TEXT": "ratio", "OP": "?"}, {"TEXT": "over", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "including"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"TEXT": "and"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}]
    # the concentration was slightly increased by 8.8%
    pattern_7 = [{"LOWER": {"IN": ["overall", "the"]}}, {"TEXT": {"IN": [",", "concentration"]}}, {"LEMMA": {"IN": ["it", "be"]}}, {"TEXT": "slightly", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "by"}, {"TEXT": "an", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"TEXT": "of", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # A significant reduction by 44.8% was observed in Mumbai
    pattern_8 = [{"TEXT": {"IN": ["the", "A"]}}, {"TEXT": {"IN": ["percentage", "significant"]}}, {"LEMMA": {"IN": trend}}, {"LEMMA": {"IN": ["be", "by"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": "observe", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}]
    # The largest reduction was measured in the city of Milan (57.6%), followed by the SaA (49.1%) and SaB (32%)
    pattern_15 = [{"LOWER": "the"}, {"TEXT": "largest"}, {"LEMMA": {"IN": trend}}, {"LEMMA": "be"}, {"LEMMA": "measure"}, {"TEXT": "in"}, {"TEXT": "the"}, {"TEXT": "city"}, {"TEXT": "of"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"LEMMA": "follow"}, {"TEXT": "by"}, {"TEXT": "the"}, {"TEXT": "SaA"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": "and"}, {"TEXT": "SaB"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}]

    # #### BRACKET PATTERNS #### #
    pol_after_number_pattern = [{"TEXT": "lockdown"}, {"TEXT": "emission"}, {"LEMMA": {"IN": trend}}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}]
    # 65% decrease in NO2
    second_basic_pattern = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "fractional", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"LEMMA": "observe", "OP": "?"}, {"TEXT": {"IN": ["of", "in"]}}, {"TEXT": "the", "OP": "?"}, {"TEXT": {"IN": ["surface", "tropospheric"]}, "OP": "?"}, {"TEXT": "emission", "OP": "?"}, {"TEXT": "of", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}]
    # decreases in NO2 levels in San Francisco and Bakersfield of about 20%
    long_pattern_2 = [{"LEMMA": {"IN": trend}}, {"TEXT": "value", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "p", "OP": "?"}, {"TEXT": "<", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": {"IN": ["of", "in", "be", "average"]}}, {"LEMMA": "observe", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"LEMMA": {"IN": ["concentration", "emission"]}, "OP": "?"}, {"TEXT": {"IN": ["for", "of"]}, "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": ["concentration", "level"]}, "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": ["record", "observe"]}, "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"TEXT": "San", "OP": "?"}, {"TEXT": "Francisco", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"LEMMA": {"IN": ["be", "of", "by", "("]}}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": "S3a", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "slightly", "OP": "?"}, {"TEXT": {"IN": ["less", "higher"]}, "OP": "?"}, {"TEXT": "at", "OP": "?"}, {"TEXT": "UT", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"IN": ["only", "about"]}, "OP": "?"}, {"TEXT": "�", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")", "OP": "?"}, {"TEXT": {"IN": ["than", "and", "vs."]}, "OP": "?"}, {"TEXT": {"IN": ["at", "followed"]}, "OP": "?"}, {"TEXT": {"IN": ["UB", "by"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "�", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "whereas", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "a", "OP": "?"}, {"TEXT": "non", "OP": "?"}, {"TEXT": "-", "OP": "?"}, {"TEXT": "significant", "OP": "?"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": "find", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}]
    # reductions in tropospheric NO2 columns of approximately 40%, 38%, and 20%
    pattern_a = [{"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["their", "in"]}}, {"TEXT": "tropospheric", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "columns", "OP": "?"}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": {"IN": ["by", "of"]}}, {"TEXT": "approximately", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # Beijing (31%), Hebei (22%), Shanghai (20%), Shandong (24%), and Hubei (32%), where the NO2 concentrations decrease
    pattern_b = [{"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"TEXT": {"IN": ["and", "where"]}}, {"TEXT": {"IN": ["the", "their"]}}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"LEMMA": {"IN": trend}}]
    # decrease of PM2.5 concentration (DR < 5%) is observed in Jiangxi (5%), Guangdong (4%), Guangxi (0%), Chongqing (5%), and
    pattern_d = [{"LEMMA": {"IN": trend}}, {"TEXT": "rate", "OP": "?"}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": {"IN": ["(", "during", "from"]}, "OP": "?"}, {"TEXT": {"IN": ["DR", "COVID-19", "P1"]}, "OP": "?"}, {"TEXT": {"IN": ["<", ",", "to"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": {"IN": ["%", "and", "P4"]}, "OP": "?"}, {"TEXT": {"IN": [")", "they"]}, "OP": "?"}, {"LEMMA": {"IN": ["be", "which", ","]}, "OP": "?"}, {"LEMMA": {"IN": ["observe", "which"]}, "OP": "?"}, {"LEMMA": {"IN": ["in", "include"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "("}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}]
    # increase of PM10 concentration by 3% and 8%
    pattern_e = [{"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["in", "of"]}}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": {"IN": ["during", "with"]}, "OP": "?"},{"TEXT": "the", "OP": "?"}, {"TEXT": {"IN": ["lockdown", "a"]}, "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": ["quite", "observe"]}, "OP": "?"}, {"TEXT": {"IN": ["variable", "across"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "ranging", "OP": "?"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"TEXT": "ratio", "OP": "?"}, {"TEXT": {"IN": ["by", "of", "from", "between", "ranged"]}}, {"TEXT": "about", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "SaA", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}]
    # PM2.5 concentrations exhibit notable domain-wide reductions in E1 2020 in Figure 1b; the changes are 􀀀2.04  1.57 g m􀀀3 in Figure 1c and 􀀀27.25  23.88%
    pattern_f = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "concentrations", "OP": "?"}, {"TEXT": {"IN": ["indicate", "exhibit"]}}, {"TEXT": {"IN": ["widespread", "notable"]}}, {"TEXT": "domain", "OP": "?"}, {"TEXT": "-", "OP": "?"}, {"TEXT": "wide", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["between", "in"]}}, {"TEXT": {"IN": ["the", "E1"]}}, {"TEXT": "ﬁve", "OP": "?"}, {"TEXT": "-", "OP": "?"}, {"TEXT": "year", "OP": "?"}, {"TEXT": "historical", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"TEXT": "2020", "OP": "?"}, {"TEXT": "in"}, {"TEXT": "Figure"}, {"TEXT": {"IN": ["1e", "1b"]}}, {"TEXT": "and", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "2020", "OP": "?"}, {"TEXT": "lockdown", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"TEXT": "Figure", "OP": "?"}, {"TEXT": "1f", "OP": "?"}, {"TEXT": ";"}, {"TEXT": "the"}, {"TEXT": "changes"}, {"TEXT": "are"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "±"}, {"TEXT": {"REGEX": number_regex}}, {"POS": "ADP", "OP": "?"}, {"TEXT": {"IN": ["ppb", "m−3"]}}, {"TEXT": "in"}, {"TEXT": "Figure"}, {"TEXT": {"IN": ["1", "1c"]}}, {"TEXT": "g", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "±"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"} ]
    # decrease by 35% for NO2
    pattern_m = [{"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["of", "by", "averaging"]}}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "–", "OP": "?"}, {"TEXT": {"IN": ["approximately", "~"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": "observe", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": "ADP", "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": {"IN": ["in", "for"]}}, {"TEXT": "the", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}]
    # decrease with the Covid-19 controls was NO2 (ACV=−54%)
    pattern_t = [{"LEMMA": {"IN": trend}}, {"TEXT": "with"}, {"TEXT": "the"}, {"LOWER": "covid-19"}, {"TEXT": "controls"}, {"LEMMA": "be"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "("}, {"TEXT": "ACV"}, {"TEXT": "="}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # CO in Shenzhen, Guangzhou, and Foshan in 2020 decreased by 15.6%, 21.8%, and 29.3%
    pattern_v = [{"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": ["be", "in", ","]}}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["found", "and", "observed", "which", "despite"]}}, {"POS": "PROPN", "OP": "?"}, {"LEMMA": {"IN": ["from", "in", "to", "be", "have", "the"]}, "OP": "?"}, {"LEMMA": "observe", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"TEXT": {"IN": ["be", "to", "significant", "absence"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["significantly", "2020", "be", "markedly", "emissions", "of"]}, "OP": "?"}, {"TEXT": "data", "OP": "?"}, {"TEXT": "relating", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "p", "OP": "?"}, {"TEXT": "<", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "from", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "SaB", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": "SaA", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "concentration", "OP": "?"}, {"TEXT": "transport", "OP": "?"}, {"TEXT": "sector", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "on", "OP": "?"}, {"TEXT": "an", "OP": "?"}, {"TEXT": {"IN": ["average", "significantly"]}, "OP": "?"}, {"TEXT": {"IN": ["(", "by", "from"]}}, {"TEXT": "the", "OP": "?"}, {"TEXT": "CTRL", "OP": "?"}, {"TEXT": "period", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "PL", "OP": "?"}, {"TEXT": "phase", "OP": "?"}, {"TEXT": "p", "OP": "?"}, {"TEXT": "<", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "during", "OP": "?"}, {"TEXT": "lockdown", "OP": "?"}, {"TEXT": "period", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "by", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "over", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["-", "and"]}}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": "non", "OP": "?"}, {"TEXT": "-", "OP": "?"}, {"TEXT": "significant", "OP": "?"}, {"LEMMA": {"IN": trend}, "OP": "?"}, {"TEXT": "by", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}]
    # NO2, the daily delta is negative for all countries, ranging from −13.0% (urban) and −9.7% (rural) for the lowest delta in Sweden to −57.8% (urban) and −53.6% in Portugal
    pattern_3 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": "the"}, {"TEXT": "daily"}, {"TEXT": "delta"}, {"LEMMA": "be"}, {"LEMMA": {"IN": trend}}, {"TEXT": "for"}, {"TEXT": "all"}, {"TEXT": "countries"}, {"TEXT": ","}, {"TEXT": "ranging"}, {"TEXT": "from"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "urban"}, {"TEXT": ")"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "rural"}, {"TEXT": ")"}, {"TEXT": "for"}, {"TEXT": "the"}, {"TEXT": "lowest"}, {"TEXT": "delta"}, {"TEXT": "in"}, {"POS": "PROPN"}, {"TEXT": "to"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "urban"}, {"TEXT": ")"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # NO2 reduction (61.6% and 60.2%), followed by Bangalore (48.2%), Ahmedabad (46.70%), Nagpur (46.20%), Gandhi Nagar (45.5%) and Mumbai (43.1%)
    pattern_9 = [{"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": trend}}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"TEXT": "followed"}, {"TEXT": "by"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ","}, {"POS": "PROPN"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"POS": "PROPN"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}]
    # NO2 decrease was observed (Fig. S4a), most pronounced at UT (43.9%) than at UB (27.4%)
    pattern_12 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "levels", "OP": "?"}, {"LEMMA": {"IN": ["do", "show"]}, "OP": "?"}, {"TEXT": "not", "OP": "?"}, {"TEXT": "signiﬁcantly", "OP": "?"}, {"TEXT": "change", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": {"REGEX": "S[1-9]b"}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"LEMMA": "exhibit", "OP": "?"}, {"TEXT": "an", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "highest", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"LEMMA": {"IN": ["to", "be", "among", "of"]}}, {"LEMMA": {"IN": ["a", "observe", "all"]}, "OP": "?"}, {"TEXT": {"IN": ["the", "higher"]}, "OP": "?"}, {"TEXT": {"IN": ["considered", "extent"]}, "OP": "?"}, {"TEXT": {"IN": ["urban", "than"]}, "OP": "?"}, {"TEXT": {"IN": ["areas", "in"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": {"REGEX": "S[1-9]a"}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "most", "OP": "?"}, {"TEXT": {"IN": ["averaging", "pronounced"]}, "OP": "?"}, {"TEXT": "at", "OP": "?"}, {"TEXT": "UT", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "�", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "at", "OP": "?"}, {"TEXT": {"IN": ["SB", "UT"]}, "OP": "?"}, {"TEXT": {"IN": ["and", "than"]}}, {"TEXT": "at", "OP": "?"}, {"TEXT": "UB", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "�", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # PM10 remained basically unchanged (Fig. S2c), showing a 7.6% reduction
    pattern_13 = [{"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"LEMMA": "remain", "OP": "?"}, {"TEXT": "basically", "OP": "?"}, {"TEXT": "unchanged", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": {"REGEX": "S[1-9]c"}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"POS": "NUM", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "which", "OP": "?"}, {"LEMMA": {"IN": ["be", "show"]}}, {"TEXT": "a", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "(", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "/", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"LEMMA": {"IN": trend}}]
    # O3 increase (Fig. S5b), averaging 14.7% at SB and 8% at
    pattern_14 = [{"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"TEXT": "PL", "OP": "?"}, {"LEMMA": "have", "OP": "?"}, {"TEXT": "a", "OP": "?"}, {"TEXT": "substantial", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "(", "OP": "?"}, {"TEXT": "Fig", "OP": "?"}, {"TEXT": ".", "OP": "?"}, {"TEXT": {"REGEX": "S[1-9]b"}, "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"LEMMA": "range", "OP": "?"}, {"TEXT": {"IN": ["by", "averaging", "of", "between", "before"]}}, {"TEXT": "(", "OP": "?"}, {"TEXT": "–", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": ["in", "at"]}, "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": "SB", "OP": "?"}, {"TEXT": ")", "OP": "?"},{"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": "in", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"POS": "ADP", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "–", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "respectively", "OP": "!"}]
    # 70% and 20–30% NO2 reduction
    pattern_22 = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": trend}}]

    # #### MULTI PATTERNS #### #
    multi_pattern = [{"LEMMA": {"IN": trend}}, {"TEXT": "of"}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": "and"}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": ["in", "for"]}}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}]
    second_multi_pattern = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"TEXT": "in"}, {"TEXT": "the"}, {"TEXT": "concentration"}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}]
    two_pattern_reverse = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"LEMMA": "be"}, {"TEXT": "found"}, {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}]
    # REDUCTION was estimated for BC and NO2 (−45 to −51%)
    pattern_g = [{"LEMMA": {"IN": trend}}, {"LEMMA": "be", "OP": "?"}, {"TEXT": "estimated", "OP": "?"}, {"TEXT": {"IN": ["in", "for"]}, "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": {"IN": ["emissions", "("]}, "OP": "?"}, {"TEXT": {"IN": ["of", "by"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%", "OP": "?"}, {"TEXT": {"IN": ["and", "to"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # NO2 reduced by 27.0%, PM2.5 by 10.5%, PM10 by 21.4% and CO by 12.1%.
    pattern_i = [{"TEXT": {"IN": pollutants_no_number}}, {"POS": "NOUN", "OP": "?"}, {"POS": "NOUN", "OP": "?"}, {"POS": "NOUN", "OP": "?"}, {"POS": "NOUN", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"POS": "ADV", "OP": "?"}, {"POS": "ADV", "OP": "?"}, {"TEXT": {"IN": ["(", "by"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")", "OP": "?"}, {"POS": "ADJ", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"POS": "ADJ", "OP": "?"}, {"POS": "ADJ", "OP": "?"}, {"POS": "ADJ", "OP": "?"}, {"POS": "NOUN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"POS": "VERB", "OP": "?"}, {"TEXT": "by", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": {"IN": ["(", "by"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": {"IN": ["(", "by"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": {"IN": ["(", "by"]}, "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}]
    # decreased by 13.7%, 21.8%, 12.2%, 4.6%, and 46.1% on average for PM2.5, PM10, CO, SO2, and NO2
    pattern_j = [{"LEMMA": {"IN": trend}}, {"LEMMA": "concentration", "OP": "?"}, {"LEMMA": {"IN": ["of", "by", "be"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": {"IN": ["in", "on"]}, "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"TEXT": "concentration", "OP": "?"}, {"TEXT": {"IN": ["of", "for"]}}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": {"IN": ["ADP", "PROPN"]}, "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": {"IN": ["ADP", "PROPN"]}, "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": {"IN": ["ADP", "PROPN"]}, "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}]
    # decreased by 42.7% for PM2.5, 47.9% for PM10, 28.6% for SO2, 22.3% for CO and 58.4% for NO2
    pattern_o = [{"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["of", "by"]}}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": "ADP", "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": {"IN": ["in", "for"]}}, {"POS": "SPACE", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": "ADP", "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": {"IN": ["in", "for"]}}, {"POS": "SPACE", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": "for", "OP": "?"}, {"POS": "SPACE", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": ","}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": "for", "OP": "?"}, {"POS": "SPACE", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}, "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": "~", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "from", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"POS": {"IN": ["ADP", "PROPN"]}, "OP": "?"}, {"TEXT": "m–3", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": {"IN": ["in", "for"]}}, {"POS": "SPACE", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}]
    # PM2.5, PM10, SO2, NO2 and CO in 2020 decrease by 14%, 15%, 12%, 16% and 12%
    pattern_p = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "in", "OP": "?"}, {"TEXT": "2020", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "by"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # SO2, NOx, PM2.5 and VOCs have been reduced by 26%, 47%, 46% and 57%
    pattern_r = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "’s", "OP": "?"}, {"TEXT": "(", "OP": "?"}, {"TEXT": "BTEX", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "have", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": {"IN": ["to", "by"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # PM2.5, PM10, SO2, CO, and NO2 were 46.1 μg m–3, 50.8 μg m–3, 2.56 ppb, 0.60 ppm, and 6.70 ppb and were 30.1%, 40.5%, 33.4%, 27.9%, and 61.4%, respectively, lower
    pattern_s = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "be"}, {"TEXT": {"REGEX": number_regex}}, {"POS": "ADP"}, {"POS": "ADJ"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"POS": "ADP"}, {"POS": "ADJ"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"POS": "NOUN"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"POS": "NOUN"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"POS": "NOUN"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "respectively", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"LEMMA": "be"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "respectively", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"LEMMA": {"IN": trend}}]
    # NO2, SO2, and CO decreased by 45%, 47%, and 20%
    pattern_w = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["in", "at"]}, "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "studied", "OP": "?"}, {"TEXT": "area", "OP": "?"}, {"TEXT": "trafﬁc", "OP": "?"}, {"TEXT": "station", "OP": "?"}, {"TEXT": "with", "OP": "?"}, {"TEXT": "respective", "OP": "?"},{"TEXT": ",", "OP": "?"}, {"LEMMA": {"IN": ["have", "be"]}, "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"LEMMA": {"IN": ["signiﬁcant", "sharp"]}, "OP": "?"}, {"LEMMA": {"IN": trend}}, {"LEMMA": "rate", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["respectively", "significantly"]}, "OP": "?"}, {"POS": "PUNCT", "OP": "?"}, {"TEXT": {"IN": ["of", "by"]}}, {"TEXT": "approximately", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "at", "OP": "?"}, {"POS": "PROPN", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}]
    # reduction rate of CO from P1 to P4 (44.1%) was comparable to the PM2.5 (46.9%)
    pattern_x = [{"LEMMA": {"IN": trend}}, {"TEXT": "rate"}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "from"}, {"TEXT": "P1"}, {"TEXT": "to"}, {"TEXT": "P4"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"LEMMA": "be"}, {"TEXT": "comparable"}, {"TEXT": "to"}, {"TEXT": "the"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # reduction of PM2.5, PM10 and NO2 were 40%, 32% and 13%
    pattern_y = [{"LEMMA": {"IN": trend}}, {"TEXT": "in", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "average", "OP": "?"}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": ["by", "be"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # PM10 and PM2.5 have reduced by about −51.84% and −53.11%
    pattern_1 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": "the", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": ["level", "concentration"]}, "OP": "?"}, {"LEMMA": {"IN": ["be", "have"]}, "OP": "?"}, {"TEXT": {"IN": ["slightly", "significantly", "markedly"]}, "OP": "?"}, {"TEXT": "higher", "OP": "?"}, {"TEXT": "during", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "former", "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"LEMMA": "observe", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": "a", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "signiﬁcantly", "OP": "?"}, {"TEXT": {"IN": ["to", "by", "of"]}}, {"TEXT": "about", "OP": "?"}, {"TEXT": "–", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": "–", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # reduced in comparison with pre-lockdown period, namely with 45% for PM2.5 and 47% for PM10
    pattern_16 = [{"LEMMA": {"IN": trend}}, {"TEXT": "in", "OP": "?"}, {"TEXT": "comparison", "OP": "?"}, {"TEXT": "with", "OP": "?"}, {"TEXT": "pre", "OP": "?"}, {"TEXT": "-", "OP": "?"}, {"TEXT": "lockdown", "OP": "?"}, {"TEXT": "period", "OP": "?"}, {"TEXT": ","}, {"TEXT": "namely", "OP": "?"}, {"TEXT": {"IN": ["up", "with"]}}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "for"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "for"}, {"TEXT": {"IN": pollutants_no_number}}]
    # reduction ratios of NO, NO2, NOx, SO2, CO, CO2, PM2.5, OC, EC and nitrate were 86.4%, 60.5%, 72.2%, 20.6%, 36.3%, 7.7%, 29.8%, 23.1%, 41.0% and 23.9%
    pattern_17 = [{"LEMMA": {"IN": trend}}, {"LEMMA": "ratio"}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "be"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # Reductions in PM10, PM2.5, NO2, SO2, and CO are 26-31%, 23-32%, 63-64%, 9-20%, and 25-31%
    pattern_19 = [{"LEMMA": {"IN": trend}}, {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "be"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "-"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "-"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "-"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "-"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "-"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # PM2.5 and PM10 concentration, 32.29% and 33.72% reduction
    pattern_21 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}]

    # #### PLUS - MINUS PATTERNS #### #
    # PM2.5 and NO2 in northern China have decreased by approximately (29 ± 22%) and (53 ± 10%)
    pattern_h = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "in"}, {"TEXT": "northern"}, {"TEXT": "China"}, {"LEMMA": "have"}, {"LEMMA": {"IN": trend}}, {"TEXT": "by"}, {"TEXT": "approximately", "OP": "?"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "±"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}, {"TEXT": "and"}, {"TEXT": "("}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "±"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}]

    # #### LONG - NO TREND PATTERNS #### #
    # PM2.5, PM10, SO2, CO, NO2, and O3 concentrations show remarkable variations compared with those of historical averages, with -27%, -36%, -52%, -27%, -40%, and 15% changes during the first month of the lockdown period, and -32%, -30%, -48%, -38%, -29%, and 2%
    pattern_k = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}},  {"TEXT": "concentrations"}, {"TEXT": "show"}, {"TEXT": "remarkable"}, {"TEXT": "variations"}, {"TEXT": "compared"}, {"TEXT": "with"}, {"TEXT": "those"}, {"TEXT": "of"}, {"TEXT": "historical"}, {"TEXT": "averages"}, {"TEXT": ","}, {"TEXT": "with"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "changes"}, {"TEXT": "during"}, {"TEXT": "the"}, {"TEXT": "first"}, {"TEXT": "month"}, {"TEXT": "of"}, {"TEXT": "the"}, {"TEXT": "lockdown"}, {"TEXT": "period"}, {"TEXT": ","}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]

    # #### NO POLLUTANT, NO TREND PATTERNS #### #
    # change is −23.5% (urban) and −13.0% (rural)
    pattern_n = [{"TEXT": "change"}, {"LEMMA": "be"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%", "OP": "?"}, {"TEXT": "("}, {"TEXT": "urban"}, {"TEXT": ")"}, {"TEXT": {"IN": ["but", "and"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # −23.5% (urban) and −13.0% (rural) in Portugal when the largest positive change is +4.0 (urban) but −4.6%
    pattern_4 = [{"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "urban"}, {"TEXT": ")"}, {"TEXT": "and"}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "rural"}, {"TEXT": ")"}, {"TEXT": "in"}, {"POS": "PROPN"}, {"TEXT": "when", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "largest", "OP": "?"}, {"TEXT": "positive", "OP": "?"}, {"TEXT": "change", "OP": "?"}, {"LEMMA": {"IN": ["to", "be"]}}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}, {"TEXT": "("}, {"TEXT": "urban"}, {"TEXT": ")"}, {"TEXT": {"IN": ["and", "but"]}}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}]

    # #### TREND NUMBER PATTERNS #### #
    # NO2, corresponding to a −71.9%
    pattern_q = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["concentration", "corresponding"]}}, {"LEMMA": {"IN": ["be", "to"]}}, {"TEXT": "a", "OP": "?"}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}]
    # PM2.5 and PM10 were −21% and −27%
    pattern_u = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "be"}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}]
    # NO2 (−52.68%)
    pattern_z = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "("}, {"TEXT": "up", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": {"REGEX": trend_number_regex}}, {"TEXT": "%"}, {"TEXT": "and", "OP": "?"}, {"TEXT": {"REGEX": trend_number_regex}, "OP": "?"}, {"TEXT": "%", "OP": "?"}, {"TEXT": ")", "OP": "?"}]
    # NO2 (–68%)
    pattern_2 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "("}, {"TEXT": "up", "OP": "?"}, {"TEXT": "to", "OP": "?"}, {"TEXT": "–"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ")"}]

    # #### DOUBLE MULTI PATTERNS #### #
    # PM10, PM2:5, NO2 and SO2 reduced by 55%, 49%, 60% and 19%, and 44%, 37%, 78% and 39%
    pattern_5 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "have", "OP": "?"}, {"LEMMA": "be", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "by"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]

    # #### NO PERCENTAGE MULTI PATTERNS #### #
    # 43, 31, 10, and 18% decreases in PM2.5, PM10, CO, and NO2
    pattern_6 = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}]
    # PM10, PM2.5, NO2, CO, and SO2 decreased by 23, 29, 54, 6, and 52%
    pattern_18 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ","}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": trend}}, {"TEXT": "by"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]

    # #### NO PERCENTAGE BRACKET PATTERNS #### #
    # NO2 concentrations reduced by 6, 7, 8 and 20%,
    pattern_11 = [{"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration"}, {"LEMMA": "be", "OP": "?"}, {"TEXT": "almost", "OP": "?"}, {"LEMMA": {"IN": trend}}, {"TEXT": "in", "OP": "?"}, {"TEXT": "the", "OP": "?"}, {"TEXT": "TL", "OP": "?"}, {"TEXT": "phase", "OP": "?"}, {"TEXT": {"IN": ["(", "by"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"REGEX": number_regex}, "OP": "?"}, {"TEXT": ",", "OP": "?"}, {"TEXT": {"IN": ["-", "and"]}}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]
    # 53.2, 19.0, and 10.4% falls of NO2
    pattern_23 = [{"TEXT": {"REGEX": number_regex}}, {"TEXT": ","}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": ",", "OP": "?"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"LEMMA": {"IN": trend}}, {"TEXT": "of"}, {"TEXT": {"IN": pollutants_no_number}}]

    # #### TWO FOR ONE PATTERNS #### #
    # drop in AQIPM2.5 of 45.25% and 64.65% and in AQINO2 of 37.42% and 65.80%
    pattern_10 = [{"LEMMA": {"IN": trend}}, {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "of"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"},  {"TEXT": "in"}, {"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "of"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}, {"TEXT": "and"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]

    # #### TWO POLLUTANTS ONE VALUE PATTERNS #### #
    # CO and NO2 fell at High Traffic sites by 50%
    pattern_20 = [{"TEXT": {"IN": pollutants_no_number}}, {"TEXT": "and"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": {"IN": trend}}, {"TEXT": "at"}, {"LOWER": "high"}, {"POS": "PROPN"}, {"LEMMA": "site"}, {"TEXT": "by"}, {"TEXT": {"REGEX": number_regex}}, {"TEXT": "%"}]

    # #### TABLE FINDING PATTERNS #### #
    table_1 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"TEXT": "(", "OP": "?"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration", "OP": "?"}, {"TEXT": ")", "OP": "?"}, {"LEMMA": "calculate"}]
    table_2 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"LOWER": "maximum"}, {"TEXT": "daily"}, {"TEXT": "delta"}, {"OP": "*"}, {"TEXT": "of"}, {"LEMMA": "concentration"}, {"TEXT": "("}, {"TEXT": "%"}, {"TEXT": ")"}]
    table_3 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"TEXT": "%"}, {"OP": "*"}, {"TEXT": "of"}, {"OP": "*"}, {"TEXT": "daily"}, {"TEXT": "maximum"}, {"TEXT": {"IN": pollutants_no_number}}]
    table_4 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"TEXT": {"NOT_IN": ["."]}, "OP": "+"}, {"TEXT": "%"}, {"TEXT": {"NOT_IN": ["."]}, "OP": "+"}, {"LEMMA": "concentration"}]
    table_5 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"TEXT": {"NOT_IN": ["."]}, "OP": "+"}, {"LEMMA": "concentration"}, {"TEXT": {"NOT_IN": ["."]}, "OP": "+"}, {"TEXT": "%"}]
    table_6 = [{"TEXT": "Table"}, {"POS": "NUM"}, {"OP": "*"}, {"TEXT": {"NOT_IN": ["."]}, "OP": "+"}, {"TEXT": {"IN": pollutants_no_number}}, {"LEMMA": "concentration"}]

    # here we add our patterns to the different matchers and specify which function should be called
    matcher.add("no_poll_matcher", [pattern_15, pattern_8, pattern_7, no_pollutant_pattern, pattern_c, pattern_l], on_match=no_pollutant_match)
    matcher.add("bracket_matcher", [pattern, long_pattern, two_pattern, pattern_22, pattern_14, pattern_13, pattern_12, pattern_9, pattern_3, pol_after_number_pattern, second_basic_pattern, pattern_a, pattern_b, long_pattern_2, pattern_d, pattern_e, pattern_f, pattern_m, pattern_t, pattern_v], on_match=bracket_matcher)
    matcher.add("multi_matcher", [pattern_21, pattern_19, pattern_17, pattern_16, pattern_5, pattern_1, multi_pattern, second_multi_pattern, two_pattern_reverse, pattern_i, pattern_j, pattern_o, pattern_g, pattern_p, pattern_r, pattern_s, pattern_u, pattern_w, pattern_x, pattern_y], on_match=multi_matcher)
    matcher.add("plus_minus_matcher", [pattern_h], on_match=plus_minus_matcher)
    matcher.add("long_no_trend_matcher", [pattern_k], on_match=no_trend_matcher)
    matcher.add("no_pollutant_no_trend", [pattern_n, pattern_4], on_match=no_pollutant_no_trend)
    matcher.add("trend_number_matcher", [pattern_q, pattern_z, pattern_2], on_match=bracket_matcher)
    matcher.add("no_percentage_multi_matcher", [pattern_18, pattern_6], on_match=no_percentage_multi_matcher)
    matcher.add("no_percentage_bracket_matcher", [pattern_23, pattern_11], on_match=no_percentage_bracket_matcher)
    matcher.add("two_in_one_matcher", [pattern_10], on_match=two_in_one_matcher)
    matcher.add("two_pol_one_value", [pattern_20], on_match=two_pol_one_value_matcher)
    matcher.add("table_finder", [table_1], on_match=table_finder)
    matcher.add("different_pol_table", [table_2], on_match=different_pol_table)
    matcher.add("weird_layout", [table_3], on_match=huge_layout_fail_table)
    matcher.add("table_highlighter", [table_4, table_5, table_6], on_match=table_highlighter)

    # TODO
    # EASTASIA FOR TABLES and europe, europe2! world? world8?
    # check if it is a bracket or multi pattern
    # fix two in one multimatcher (thailand O3)

    # this is where we will store all the extracted data
    total_data = []

    # get the files in the directory and iterate over them
    directories = os.listdir(directory)
    directories.sort()
    for file in directories:

        if file == "README":
            continue
        
        # this is for storing the data of each file
        article_data = {}

        # dataf = tabula.read_pdf(directory + file, pages="4")
        # print(dataf)
        # page counter to keep track of visited pages
        pages = []

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

            # for tok in doc:
            #     if tok.text == "Table" and tok.nbor().text == "3":
            #         for t in tok.sent:
            #             print(t.text + " -> " + t.pos_ + " -> " + t.dep_ + " -> " + t.lemma_)

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

    # this is for listing which DOI was not found, for evaluation purposes
    """
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
    """


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
            return fix_pollutant(tok.text)
    return ""


def get_all_pollutants(sent):
    """
    This function searches a sentence for all occurring pollutants
    :param sent: the sentence that should be searched
    :return: the found pollutants
    """
    pollutants = []
    for tok in sent:
        if tok.text in pollutants_no_number:
            pol = fix_pollutant(tok.text)
            pollutants.append(pol)
    return pollutants


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

        # the last word in a sentence can't be a value, so break if that's the case
        if tok.i + 1 == len(tok.doc):
            break

        # now look for a value
        if re.search(number_regex, tok.text) and tok.nbor().text in ["to", "%", "±"]:
            if tok.nbor().text in ["to", "±"] and tok.nbor().nbor().nbor().text != "%":
                continue
            # check if the text contains more than just the number and adjust if needed
            text = tok.text
            if text[0] in ["−", "+", "~", "-"]:
                text = text[1:]
            if "b" in text:
                text = text.replace("b", "")
            if "e" in text:
                text = text.split("e")[0]
            if "%" in text:
                text = text.split("%")[0]
            if "~" in text:
                text = text.split("~")[0]
            if "–" in text[1:]:
                v = text.split("–")
                try:
                    text = str(round((float(v[0]) + float(v[1]))/2, 2))
                except ValueError:
                    print(v)
                    print("contains not only numbers")
                    print(tok.sent)
                    break
            if "-" in text[1:]:
                v = text.split("-")
                try:
                    text = str(round((float(v[0]) + float(v[1]))/2, 2))
                except ValueError:
                    print(v)
                    print("contains not only numbers")
                    print(tok.sent)
                    break
            if "−" in text[1:]:
                v = text.split("−")
                try:
                    text = str(round((float(v[0]) + float(v[1]))/2, 2))
                except ValueError:
                    print(v)
                    print("contains not only numbers")
                    print(tok.sent)
                    break
            try:
                number = float(text)
            except ValueError:
                print(tok.text + " is no number")
                print(tok.sent)
                break
            current_value = str(number)
            if down:
                current_value = "-" + current_value
            values.append(current_value)

    # we need to convert some negative numbers to positive because sometimes we find the number before the trend
    if not down:
        for j in range(len(values)):
            values[j] = values[j].replace("-", "")
    return values


def get_plus_minus_values(sent):
    """
    This function searches a sentence for values that cover a range of values.
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
        # find a number
        if re.search(number_regex, tok.text):
            # check if ± is next
            if tok.nbor().text == "±" or tok.nbor().text == "%" and tok.nbor().nbor().text == "±":
                # check if the text contains more than just the number and adjust if needed
                text = tok.text
                if text[0] in ["−", "+", "~"]:
                    text = text[1:]
                if "–" in text:
                    v = text.split("–")
                    text = str(round((float(v[0]) + float(v[1]))/2, 2))
                if "-" in text:
                    v = text.split("-")
                    text = str(round((float(v[0]) + float(v[1]))/2, 2))
                if "e" in text:
                    text = text.split("e")[0]
                if "%" in text:
                    text = text.split("%")[0]
                if "~" in text:
                    text = text.split("~")[0]
                number = float(text)
                current_value = str(number)
                if down:
                    current_value = "-" + current_value
                values.append(current_value)

    # we need to convert some negative numbers to positive because sometimes we find the number before the trend
    if not down:
        for j in range(len(values)):
            values[j] = values[j].replace("-", "")
    return values


def get_no_trend_values(sent):
    """
    This function searches a sentence for values that have the trend in front of their number.
    :param sent: the sentence that should be searched
    :return: a list of values for the pollutant
    """
    values = []
    for tok in sent:
        if tok.text not in pollutants_no_number and re.search(number_regex, tok.text):
            try:
                number = float(tok.text)
            except ValueError:
                number = "-" + str(float(tok.text[1:]))
            values.append(str(number))
    return values


def get_all_values(sent):
    """
    This function searches a sentence for all values, no matter if there is a percentage sign or not.
    :param sent: the sentence that should be searched
    :return: a list of values for the pollutant
    """
    values = []
    down = True
    for tok in sent:
        if tok.lemma_ in positive:
            down = False
        if tok.text not in pollutants_no_number and re.search(number_regex, tok.text):
            try:
                number = float(tok.text)
            except ValueError:
                number = tok.text
            number = "-" + str(number)
            values.append(number)
    if not down:
        for j in range(len(values)):
            values[j] = values[j].replace("-", "")
    return values


def fix_pollutant(pollutant):
    """
    This function converts different spellings of pollutants into one.
    :param pollutant: the pollutant that needs to be converted
    :return: the converted pollutant
    """
    if pollutant in no2_list:
        return "NO2"
    if pollutant in nox_list:
        return "NOX"
    if pollutant in co_list:
        return "CO"
    if pollutant in pm25_list:
        return "PM25"
    if pollutant in pm10_list:
        return "PM10"
    if pollutant in o3_list:
        return "O3"
    if pollutant in so2_list:
        return "SO2"
    if pollutant in nh3_list:
        return "NH3"
    if pollutant in nmvocs_list:
        return "NMVOCS"
    if pollutant in aod_list:
        return "AOD"
    if pollutant in bc_list:
        return "BC"
    if pollutant in aqi_list:
        return "AQI"
    if pollutant in bcff_list:
        return "BCFF"
    if pollutant in bcwb_list:
        return "BCWB"
    if pollutant in no3_list:
        return "NO3"
    if pollutant in so4_list:
        return "SO4"
    if pollutant in om_list:
        return "OM"
    if pollutant in pm1_list:
        return "PM1"
    if pollutant in bboa_list:
        return "BBOA"
    if pollutant in hoa_list:
        return "HOA"
    if pollutant in ooa_list:
        return "OOA"
    return pollutant


if __name__ == "__main__":
    # extract text from the pdf document
    extract_text("./Doc/articles/PDF/")
