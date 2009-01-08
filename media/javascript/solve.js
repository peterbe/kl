function __prep_slots(n) {
   var already = $('input', $('#allslots'));
   if (already.size() > n) {
      already.slice(n).remove();
   } else {
      var left = n - already.size();
      for (var i=0, left=n - already.size(); i < left; i++) 
        $('#allslots').append(
                              $('<input name="s" size="1" maxlength="1"/>').bind('keyup', on_slot_key));
   }
}

function on_length_key(event) {
   var v = this.value;
   if (v.search(/[^\d]/)> -1) {
      this.value='';
      __wrap__prep_slots(0);
   } else if (event.which==39 || event.which==38) {
      if (this.value) {
         this.value = parseInt(this.value)+1;
         __wrap__prep_slots(parseInt(this.value));
      } else {
         this.value = '1';
         __wrap__prep_slots(1);
      }   
   } else if (event.which==37 || event.which==40) {
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
   } else
     __wrap__prep_slots(parseInt(this.value));
   console.log(event.which);
}

function __wrap__prep_slots(n) {
   if (!n>=1)
     alert("Must be bigger than zero");
   else if (n>40)
     alert("Too big");
   else
     __prep_slots(n);
}


function on_slot_key(event) {
   if (event.which==39) // right arrow
     __goto_next_slot(this);
   else if (event.which==37)
     __goto_prev_slot(this);
}

function __goto_next_slot(current) {
   var is_next = false;
   $('input', $('#allslots')).each(function() {
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
   console.log(form_data);
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
   return true;
}

function __process_submission(res) {
   $('#matches').text('');
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
}

$(function() {
   if ($('#id_length').val()) {
    if ($('#id_length').val().search(/[^\d]/) > -1)
        this.value='';
      else
        __wrap__prep_slots(parseInt($('#id_length').val()));
   }
   
   $('#id_length').bind('keyup', on_length_key);
   $('input', $('#allslots')).bind('keyup', on_slot_key);
   
   var submit_options = {
      url: '/los/json/',
        type: 'GET',
        dataType: 'json',
        beforeSubmit: __before_ajaxSubmit,
        success: __process_submission
   }
   $('form#solutions').ajaxForm(submit_options);
   
});
