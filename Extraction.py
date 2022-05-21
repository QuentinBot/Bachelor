from pdfminer.high_level import extract_text
import spacy

def main():

    nlp = spacy.load("en_core_web_sm")
    pdf = extract_text("Doc/articles/malaysia.pdf")
    doc = nlp(pdf)

    for tok in doc:
        print(tok.text, "-->", tok.dep_, "-->", tok.pos_)
        if tok.text == ".":
            break


if __name__ == "__main__":
    main()
