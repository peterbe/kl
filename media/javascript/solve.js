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

$(function() {
   if ($('#id_length').val()) {
    if ($('#id_length').val().search(/[^\d]/) > -1)
        this.value='';
      else
        __wrap__prep_slots(parseInt($('#id_length').val()));
   }
   
   $('#id_length').bind('keyup', on_length_key);
   $('input', $('#allslots')).bind('keyup', on_slot_key);
});
