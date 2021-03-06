import datetime

from django.db.models.signals import post_save
from django.db import models
from django.core.cache import cache

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
#        unique_together = ('word', 'language') temporary commented out for mysql import

    word = models.CharField(max_length=40)
    language = models.CharField(max_length=5)
    length = models.IntegerField()
    part_of_speech = models.CharField(max_length=20, null=True)
    definition = models.CharField(max_length=250, null=True)
    name = models.BooleanField()
    # used for optimization
    first1 = models.CharField(max_length=1)
    first2 = models.CharField(max_length=2)
    last1 = models.CharField(max_length=1)
    last2 = models.CharField(max_length=2)

    def __unicode__(self):
        return self.word

    def __init__(self, *args, **kwargs):
        if 'word' in kwargs:
            if 'length' in kwargs:
                assert kwargs['length'] == len(kwargs['word'])
            else:
                kwargs['length'] = len(kwargs['word'])

            if 'first1' in kwargs:
                assert kwargs['first1'] == kwargs['word'][0].lower()
            else:
                kwargs['first1'] = kwargs['word'][0].lower()
            if 'first2' in kwargs:
                assert kwargs['first2'] == kwargs['word'][:2].lower()
            else:
                kwargs['first2'] = kwargs['word'][:2].lower()

            if 'last1' in kwargs:
                assert kwargs['last1'] == kwargs['word'][-1].lower()
            else:
                kwargs['last1'] = kwargs['word'][-1].lower()
            if 'last2' in kwargs:
                assert kwargs['last2'] == kwargs['word'][-2:].lower()
            else:
                kwargs['last2'] = kwargs['word'][-2:].lower()

        super(Word, self).__init__(*args, **kwargs)


def reset_word_count(sender, instance, created, **__):
    if created:
        cache_key = 'no_total_words_%s' % instance.language
        #print "cache_key", cache_key
        #print "was cached?", cache.get(cache_key) is not None
        cache.delete(cache_key)
post_save.connect(reset_word_count, sender=Word,
                  dispatch_uid="reset_word_count")

class Search(models.Model):
    """ A search is a record of someone doing a search.
    """

    class Meta:
        db_table = u'searches'
        verbose_name_plural = u'Searches'

    search_word = models.CharField(max_length=40)
    add_date = models.DateTimeField('date added', default=datetime.datetime.now,
                                    db_index=True)
    user_agent =  models.CharField(max_length=200, default=u'')
    ip_address =  models.CharField(max_length=15, default=u'')
    language = models.CharField(max_length=5, default=u'')
    search_type = models.CharField(max_length=50, default=u'')

    found_word = models.ForeignKey(Word, null=True, blank=True)

    def __unicode__(self):
        return self.search_word


def reset_search_stats(sender, instance, created, **__):
    if created:
        cache_key = 'no_searches_today_%s' % instance.language
        #print "cache_key", cache_key
        #print "was cached?", cache.get(cache_key) is not None
        cache.delete(cache_key)

        cache_key = 'no_searches_this_week_%s' % instance.language
        #print "cache_key", cache_key
        #print "was cached?", cache.get(cache_key) is not None
        cache.delete(cache_key)

post_save.connect(reset_search_stats, sender=Search,
                  dispatch_uid="reset_search_stats")


class IPLookup(models.Model):

    class Meta:
        db_table = u'ip_lookups'
        verbose_name_plural = u"IP Lookups"

    ip = models.CharField(max_length=15, unique=True, db_index=True)
    longitude = models.DecimalField(decimal_places=10, max_digits=14,
                                    null=True, blank=True)
    latitude = models.DecimalField(decimal_places=10, max_digits=14,
                                   null=True, blank=True)
    country_name = models.CharField(max_length=40)
    place_name = models.CharField(max_length=60)
    country_code = models.CharField(max_length=3)
    add_date = models.DateTimeField('date added', default=datetime.datetime.now,
                                    db_index=True)

    def __unicode__(self):
        if self.place_name and self.longitude and self.latitude:
            return u"%s (%s:%s)" % (self.place_name, self.longitude, self.latitude)
        elif self.place_name:
            return "%s (no coordinates)" % self.place_name
        else:
            return "%s (no coordinates)" % self.country_code
