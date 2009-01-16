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
   $('#loading:hidden').show();
   
   return true;
}


function __process_submission(res) {
   if (res.word_count==1)
     $('#matches').text(res.word_count + " hittad");
   if (res.word_count>1)
     $('#matches').text(res.word_count + " hittade");
   
   if (res.alternatives_truncated)
     $('#matches').text($('#matches').text() + " (men begransar till 100)");
   
   $('#alternatives div.sugg').remove();
   if (res.word_count) {
      $.each(res.words, function(i,e) {
         var all = $('<div class="sugg"></div>');
         for (var i=0, len=e.length; i<len; i++) {
            if (res.match_points[i])
              all.append($('<span class="match letter"></span>').text(e[i]));
            else
              all.append($('<span class="letter"></span>').text(e[i]));
         }
         $('#alternatives').append(all);
      });
   } else {
      $('#matches').text("None found :(");
   }
   $('#loading:visible').hide();
   
   __done_search = true;
   
}

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
   
   var submit_options = {
      url: '/los/json/',
        type: 'GET',
        dataType: 'json',
        beforeSubmit: __before_ajaxSubmit,
        success: __process_submission
   }
   $('form#solutions').ajaxForm(submit_options);
   
});
