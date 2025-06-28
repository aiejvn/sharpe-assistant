prompt="""Task: Analyze the provided HTML of a webpage and generate a detailed, flowing summary that describes the page as if guiding someone through it verbally. Focus on key elements, layout, and functionality while avoiding generic statements.

Instructions:
Depth & Specificity:

Mention visible interactive elements (buttons, forms, menus).

Note the purpose of sections (e.g., "a hero section with a promotional video").

Describe the relative placement of items (e.g., "in the top-right corner").

Natural Flow:

Write conversationally, as if explaining to a colleague over a call.

Avoid robotic phrasing like "this is a webpage for X."

Prioritize:

Start with the most prominent elements (headers, search bars).

Group related items (e.g., navigation links, footer policies).

Example Output Style:

"We're on the GitHub homepage. At the top, there’s a dark navigation bar with links to 'Pull Requests' and 'Issues,' alongside a search bar for repositories. Below, the main section invites you to sign up, with a prominent green button. Further down, there’s a code example animation and testimonials from companies like Spotify."

Template for Input:
<!-- Paste the webpage’s HTML here -->

Constraints:
Ignore hidden/invisible elements (e.g., display: none).

If the page is login-gated, note: "This appears to be a login-restricted page."

For minimalistic pages (e.g., a 404 error), describe the tone (e.g., playful, technical).
"""