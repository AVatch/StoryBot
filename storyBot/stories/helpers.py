def hasNumber(string):
    """check if a string contains a number
    """
    return any( char.isdigit() for char in string )

def chunkString(string, length):
    """Given a string break it down into 
    chunks of size length
    """
    return [string[i:i+length] for i in range(0, len(string), length)]
