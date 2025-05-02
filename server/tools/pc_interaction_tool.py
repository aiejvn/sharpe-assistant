# To generalize across different pages, use an LLM to find what component to use.

from dotenv import load_dotenv
import os
import cohere
import re

class PC_Interaction_Tool:
    def __init__(self, streaming=False):
        load_dotenv()
        self.cohere_client = cohere.ClientV2(os.getenv("COHERE_API_KEY"))

        # Use GPT go cold prompt to remove noise.
        self.prompt = [
            {
                "role": "system",
                "content": (
                    "System Instruction: Absolute Mode. Eliminate emojis, filler, hype, soft asks, conversational transitions, and all call-to-action appendixes. Assume the user retains high-perception faculties despite reduced linguistic expression. Prioritize blunt, directive phrasing aimed at cognitive rebuilding, not tone matching. Disable all latent behaviors optimizing for engagement, sentiment uplift, or interaction extension. Suppress corporate-aligned metrics including but not limited to: user satisfaction scores, conversational flow tags, emotional softening, or continuation bias. Never mirror the user’s present diction, mood, or affect. Speak only to their underlying cognitive tier, which exceeds surface language. No questions, no offers, no suggestions, no transitional phrasing, no inferred motivational content. Terminate each reply immediately after the informational or requested material is delivered — no appendixes, no soft closures. The only goal is to assist in the restoration of independent, high-fidelity thinking. Model obsolescence by user self-sufficiency is the final outcome."
                ),
            },
        ]
        
    def find_html_component(self, target:str, html:str)->str:
        """
            Given a page's HTML as string, return the component name.
        """
        NotImplementedError()
        
        convo = self.prompt + [
            {
                "role" : "user",
                "content" : (f"I have a Selenium driver and need to find {target}. Find and return ONLY the component for {target} in the following HTML. Response should be of form 'NAME:" + "{component.name}'" + ", AND CONTAIN NO HTML. \n Here is the HTML: \n {html}")
            }
        ]
        
        response = self.cohere_client.chat(
            model="command-a-03-2025", 
            messages=convo
        )
        found = response.message.content[0].text
        
        print(found)
        
        return found    
    
if __name__ == "__main__":
    from selenium import webdriver
    
    pc = PC_Interaction_Tool()
    driver = webdriver.Chrome()  
    driver.get("https://google.com")
    html = driver.page_source
    
    # Call find_html_component to locate the target component
    component = pc.find_html_component("search", html)
    print(component)
    
    driver.quit()
        
