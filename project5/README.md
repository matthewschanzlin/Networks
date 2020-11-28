## High Level Approach
My high level approach was to get each request type working. Once each individual request was working I wrote the logic that crawled the website. It was a fairly straight forward implementation of Breadth first search on the url links. I found this project overall enjoyable.

## Challenges
My biggest challenge was fixing my format of the POST request. for the longest time I thought I had incorrect headers and then I realized I was entering my username and password incorrectly. Upon fixing this the rest of the project went fairly smoothly.

## Testing
I tested my webcrawler one "request" at a time. I got the initial get request format working then I proceeded to the post, then the get requests that crawled across the fakebook site.

The way I tested each request followed this format:

1. Analyze request from browser via dev tools. Sketch up the necessary headers/body params if necessary.
2. Print the request and its response to console
3. If the response code was incorrect I checked piazza and carefully looked over my browser request format
4. Once the format was correct I went onto the next incremental request

The actual crawling algorithm was fairly simple, I just implemented a form of BFS and found it to be decent although multithreading among other things could improve it.
