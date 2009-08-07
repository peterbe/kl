// A variable that helps us tell us that a search has been done. This can be
// used to understand that we should reset the form if someone changes the
// length.
var __done_search = null;

function __prep_slots(n) {
   var already = $('input', $('#allslots'));
   if (already.size() > n) {
      already.slice(n).remove();
   } else {
      var left = n - already.size();
      for (var i=0, left=n - already.size(); i < left; i++) 
        $('#allslots').append(
                              $('<input name="s" size="1" maxlength="1"/>')
                              .attr('autocomplete','off')
                              .bind('keyup', on_slot_key)
                              .bind('change', on_slot_change));
   }
}

function on_length_key(event) {
   var v = this.value;
   if (v.search(/[^\d]/)> -1) {
      this.value='';
      if($('#allslots input').size())
	__wrap__prep_slots(0);
   } else if (event.which==39 || event.which==38) {  // right & up
      if (this.value) {
         this.value = parseInt(this.value)+1;
         __wrap__prep_slots(parseInt(this.value));
      } else {
         this.value = '1';
         __wrap__prep_slots(1);
      }   
   } else if (event.which==37 || event.which==40) { // left & down
      if (this.value) {
         if ((parseInt(this.value)-1) < 1) 
           __wrap__prep_slots(1);
         else {
            this.value = parseInt(this.value)-1;
            __wrap__prep_slots(parseInt(this.value));
         }
      } else {
         this.value = '1';
         __wrap__prep_slots(1);
      }  
   } else {
      if (__done_search) {
	 __prep_slots(0);
      }
      __wrap__prep_slots(parseInt(this.value));
      
      __done_search = false;
   }
}

function on_length_change(event) {
   // check that the slots have been created
   var v = this.value;
   if (v && v.search(/[^\d]/) ==-1 && parseInt(v) != $('#allslots input').size())
     __wrap__prep_slots(parseInt(v));
}

function __wrap__prep_slots(n) {
   if (n<1)
     alert("Must be bigger than zero");
   else if (n>40)
     alert("Too big");
   else
     __prep_slots(n);
}


function on_slot_key(event) {
   if (event.which==39) // right arrow
     __goto_next_slot(this);
   else if (event.which==37) // left arrow
     __goto_prev_slot(this);
   else
     this.value = this.value.toUpperCase();
}

function on_slot_change(event) {
   if (!this.value) return;
   if (this.value.match(/\d/)) this.value='';
}

function __goto_next_slot(current) {
   var is_next = false;
   $('#allslots input').each(function() {
      if (is_next) {
         this.focus();
         this.select();
         is_next = false;
      } else if(this==current) is_next = true;
      
   });
}

function __goto_prev_slot(current) {
   var prev = null;
   $('input', $('#allslots')).each(function() {
      if(this==current && prev) {
         prev.focus(); 
         prev.select();
      }
      prev = this;
      
   });
}

function __before_ajaxSubmit(form_data, form_obj) {
   var length = parseInt($('#id_length').val());
   if(isNaN(length)) {
      if ($('#allslots input').size())
	$('#id_length').val($('#allslots input').size());
      else {
	 $('#id_length').addClass('error').bind('focus', function() {
	    $(this).removeClass('error');
	 });
      }
      return false;
   }
   var any_s = false;
   $('#allslots input').each(function() {
      if ($(this).val())
        any_s = true;
   });
   if (!any_s) {
      $('#error__no_s').show();
      setTimeout(function() {
         $('#error__no_s').fadeOut(500);
      }, 3*1000);
      return false;
   }
   // make sure the for-example is hidden
   $('#for-example:visible').hide();
   
   $('#loading:hidden').show();
   
   
   
   return true;
}

var _original_document_title = null;

function __update_document_title(result) {
   if (_original_document_title)
      document.title = result + " - " + $.trim(document.title.split('-')[1]);
   else {
      _original_document_title = document.title;
      document.title = result + " - " + $.trim(document.title.split('-')[0]);
   }
}


function __process_submission(res) {
    
   // make sure any error messages are hidden
   $('div.error:visible').hide();

   __update_document_title(res.match_text);
   if (res.word_count>=1)
     $('#matches').text(res.match_text);
   if (res.alternatives_truncated) {
      $('#clues').show();
      $('#notletters').show();
   } else {
      $('input', '#clues').val('');
      $('#clues').hide();
   }
   
   //if (res.alternatives_truncated)
   //  $('#matches').text($('#matches').text() + " (men begransar till 100)");
   
   $('#alternatives div.sugg').remove();
   var all, w;
   if (res.word_count) {
      $.each(res.words, function(i,r) {
         all = $('<div class="sugg"></div>');
         e = r.word;
         for (var i=0, len=e.length; i<len; i++) {
            if (res.match_points[i])
              all.append($('<span class="match letter"></span>').text(e.charAt(i)));
            else
              all.append($('<span class="letter"></span>').text(e.charAt(i)));
         }
         if (r.by_clue)
           all.append($('<span class="by_clue"></span>').text('~ ' + r.by_clue));
         if (r.definition)
           all.append($('<em class="definition"></em>').text(r.definition));
         $('#alternatives').append(all);
      });
   } else {
      $('#matches').text(res.match_text);
   }
   $('#loading:visible').hide();
   
   $('#clear-search').show();
   __done_search = true;
   
}

function __error_ajaxSubmit(request, response_text) {
   $('#error__ajax').show();
   $('#error__ajax .response').text(response_text);
}

function run_example(l, w) {
   $('#id_length').val(l);
   __prep_slots(l);
   $.each(w, function(i, e) {
      //console.log($('input', '#allslots')[1]);
      $('input', '#allslots')[i].value = e;
   });
   $('#for-example').hide(500);
   setTimeout(function() {
      $('form#solutions').ajaxSubmit(submit_options);
   }, 500);
   
}



function __check_notletters(s) {
   function uniqify(array) {
      var seen=new Array();
      $.each(array, function(i,a) {
         if ($.inArray(a, seen) == -1) seen.push(a);
      });
      return seen;
   }
   s = s.toUpperCase();
   s = s.replace(/[\d\W]+/g, '');
   
   var x = uniqify(s.match(/\w/g));
   
   $('#allslots input').each(function() {
      var v = $(this).val();
      if (v && $.inArray(v, x) > -1)
        x = $.grep(x, function(a) {
           return a != v;
        });
   });
   
   if (x.length)
     return x.join(', ') + ', ';
   return '';
}

var submit_options = {
   url: '/los/json/',
     type: 'GET',
     dataType: 'json',
     error: __error_ajaxSubmit,
     beforeSubmit: __before_ajaxSubmit,
     success: __process_submission
};

$(function() {
   if ($('#id_length').val()) {
    if ($('#id_length').val().search(/[^\d]/) > -1)
        this.value='';
      else
        __wrap__prep_slots(parseInt($('#id_length').val()));
   }
   
   $('#id_length').bind('keyup', on_length_key).bind('change', on_length_change);
   if (!$('#id_length').val())
     $('#id_length')[0].focus();
   
   $('form#solutions').ajaxForm(submit_options);
   
   $('input[name="clues"]', '#solutions').bind('keyup', function() {
      if ($(this).attr('size') <= 12 && $(this).val().indexOf(',') > -1) {
         $(this).attr('size', parseInt($(this).attr('size')) * 2);
         $(this).unbind('keyup');
      }
   });
   
   $('input[name="notletters"]', '#notletters').bind('keyup', function(event) {
      //console.log(event.keyCode);
      if (event.keyCode > 15)
        $(this).val(__check_notletters($(this).val()));
   });   
   
   
});
