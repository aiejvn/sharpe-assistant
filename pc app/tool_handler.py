import string
import sys

from desktop_tools.chrome_tool import ChromeTool

class ClientToolHandler:
    def __init__(self):
        self.chrome = ChromeTool(system=sys.platform)

    def handle_input(self, text):
        translator = str.maketrans('', '', string.punctuation)
        terms = text.split()
        if len(terms) < 2:
            return (1, "Error: input must contain at least 2 terms.")
        
        print("TERMS:", terms)
        print(terms[0].lower().translate(translator))
        print(terms[1].lower().translate(translator))
        try:
            match terms[0].lower().translate(translator):
                case "desktop":
                    match terms[1].lower().translate(translator):
                        case "search":
                            query = ""
                            for word in terms[2:]:
                                query += f"{word} "
                            self.chrome.search_google_chrome(query)
                            status, res = self.chrome.form_submit_chrome("q")
                            print(status, res)
                            
        except Exception as e:
            return (1, "Could not find tools. Error " + e)