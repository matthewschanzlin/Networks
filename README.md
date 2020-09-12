I first tried to get the parameter logic working as desired, then I attempted to get the
socket working. I was able to get the basic socket working without to many issues however I
ran into some problems with the FIND messages. My problem was that I could get the first
one and all of its data, but the server would always close its connection even though
my counts were correct. The reason for this is because of the way I attempted to get
more information. I would continue recv'ing more information and my condition for
stopping this loop was when the recv call returned data with len() = 0. Apparently
this 1 extra recv call that gets 0 data (after all data has been procured) causes
the server to shut down its connection. I am not sure why this is sense extra recv
calls don't seem like a problem since the server can just return 0 data and continue
waiting for the send message with the count. Creating the ssl socket was very straight
forward, the only issue I ran into was that I accidentally used the 27993 port for about
an hour and was very confused why I couldn't get my code to work. Other than these challenges
this project was fairly straight forward.

The only way I tested my program was by running it with some print statements to verify
that the server was interacting with my client as expected.
