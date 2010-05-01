def func1(a):
    """
    This should fail mutation testing (we don't test edge cases of a=5, a=6)
    
    >>> func1(4)
    False
    >>> func1(8)
    True
    """
    if a > 5:
        return True
    return False
    
def func2(a):
    """
    This should pass mutation testing.
    
    >>> func2(4)
    False
    >>> func2(5)
    False
    >>> func2(6)
    True
    >>> func2(7)
    True
    """
    if a > 5:
        return True
    return False