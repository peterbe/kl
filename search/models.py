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
        unique_together = ('word', 'language')
    
    word = models.CharField(max_length=40)
    language = models.CharField(max_length=5)
    length = models.IntegerField()
    part_of_speech = models.CharField(max_length=20, null=True)
    definition = models.CharField(max_length=250)
    name = models.BooleanField()
    
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
        verbose_name_plural = u'Searches'
        
    search_word = models.CharField(max_length=40)
    add_date = models.DateTimeField('date added', default=datetime.datetime.now)
    user_agent =  models.CharField(max_length=200, default=u'')
    ip_address =  models.CharField(max_length=15, default=u'')
    language = models.CharField(max_length=5, default=u'')
    search_type = models.CharField(max_length=50, default=u'')
    
    found_word = models.ForeignKey(Word, null=True, blank=True)
    
    def __unicode__(self):
        return self.search_word
    
    
class IPLookup(models.Model):
    
    class Meta:
        db_table = u'ip_lookups'
        verbose_name_plural = u"IP Lookups"
        
    ip = models.CharField(max_length=15)
    longitude = models.DecimalField(decimal_places=10, max_digits=14,
                                    null=True, blank=True)
    latitude = models.DecimalField(decimal_places=10, max_digits=14,
                                   null=True, blank=True)
    country_name = models.CharField(max_length=40)
    place_name = models.CharField(max_length=60)
    country_code = models.CharField(max_length=3)
    add_date = models.DateTimeField('date added', default=datetime.datetime.now)
    
    def __unicode__(self):
        if self.place_name and self.longitude and self.latitude:
            return u"%s (%s:%s)" % (self.place_name, self.longitude, self.latitude)
        elif self.place_name:
            return self.place_name
        else:
            return self.country_code
        
    


    