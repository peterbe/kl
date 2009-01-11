from django.db import models

# Create your models here.

class Word(models.Model):
    """
    A Word has two important parts: the word, its length 
    and there's also the optional part_of_speech. The length always
    has to be that of the word:
    
        >>> w = Word.objects.create(word=u'Peter',
        ...                         part_of_speech=u'egenamn')
        >>> w.length == len(u'Peter')
        True
        
    The field 'word' is supposed to be unique:
    
        >>> w = Word.objects.create(word=u'Peter')
        Traceback (most recent call last):
        ...
        IntegrityError: duplicate key value violates unique constraint ...
        
    """
    class Meta:
        db_table = u'words'
    
    word = models.CharField(max_length=40, unique=True)
    length = models.IntegerField()
    part_of_speech = models.CharField(max_length=20, null=True)
    
    def __unicode__(self):
        return self.word
    
    def __init__(self, *args, **kwargs):
        if 'word' in kwargs:
            if 'length' in kwargs:
                assert kwargs['length'] == len(kwargs['word'])
            else:
                kwargs['length'] = len(kwargs['word'])
        super(Word, self).__init__(*args, **kwargs)
    

