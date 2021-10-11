
# Configuration

Please make sure to have the Aurora in linking mode to generate the token. (holding the power button until the light flash).  Then enter and save the IP address.  If successful, the node server will get a token from the Nanoleaf and discover the existing devices.

If you do have a token already then you can create a custom variable token -> token\_string and it will use this token rather than querying for a new token.

If you want to reset the token or the ip of the nanoleaf, add a custom variable requestNewToken -> 1, to force rebuild of the cache.

After the first run, I suggest you click on the Rebuild Profile of the Aurora and restart the Admin Console. This will provide you with and updated list of Effect for your Aurora. If you use more then one Aurora make sure your Effect List are the same. 

NOTE : Everytime you Rebuild your effect list you need to restart ISY Admin Console for the change to take effect.
