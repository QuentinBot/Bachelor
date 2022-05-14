from pdfminer.high_level import extract_text


def main():

    pdf = extract_text("Doc/articles/malaysia.pdf")

    for c in pdf:
        print(c, end="")


if __name__ == "__main__":
    main()
