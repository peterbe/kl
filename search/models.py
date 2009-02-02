import datetime

from django.db import models

# Create your models here.

class Word(models.Model):
    """
    A Word has two important parts: the word, its length 
    and there's also the optional part_of_speech. The length always
    has to be that of the word:
    
        >>> w = Word.objects.create(word=u'Peter',
        ...                         part_of_speech=u'egenamn',
        ...                         language='sv')
        >>> w.length == len(u'Peter')
        True
        
    """
    class Meta:
        db_table = u'words'
    
    word = models.CharField(max_length=40)
    language = models.CharField(max_length=5)
    length = models.IntegerField()
    part_of_speech = models.CharField(max_length=20, null=True)
    
    unique_together = ('word', 'language')
    
    def __unicode__(self):
        return self.word
    
    def __init__(self, *args, **kwargs):
        if 'word' in kwargs:
            if 'length' in kwargs:
                assert kwargs['length'] == len(kwargs['word'])
            else:
                kwargs['length'] = len(kwargs['word'])
        super(Word, self).__init__(*args, **kwargs)
    

class Search(models.Model):
    """ A search is a record of someone doing a search. 
    """
    
    class Meta:
        db_table = u'searches'
        
    search_word = models.CharField(max_length=40)
    add_date = models.DateTimeField('date added', default=datetime.datetime.now)
    user_agent =  models.CharField(max_length=200, default=u'')
    ip_address =  models.CharField(max_length=15, default=u'')
    language = models.CharField(max_length=5, default=u'')
    
    found_word = models.ForeignKey(Word, null=True, blank=True)
    
    def __unicode__(self):
        return self.search_word
    