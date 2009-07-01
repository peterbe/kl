function __clean_slots(slots) {
  slots = slots.toUpperCase();
  slots = slots.replace(' ','_');
  slots = slots.replace('*','_');
  if (/\d/.test(slots)) {
     slots = slots.replace(/\d/, '');
     alert("Only alphabetic characters allowed");
  }
  return slots;
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

function __word2id(word) {
   return word.replace(/[^a-z]/gi,'_');
}


function __before_ajaxSubmit(form_data, form_obj) {
   var v = $('#id_slots').val();
   if (!v.length) return false;
   if (v.length==1) {
     $('#id_slots').addClass('error');
     return false;
   }
   if (!v.replace(/[\._]/g,'').length) {
     // nothing but wildcards
     $('#id_slots').addClass('error');
     return false;
   }
   
   $('#id_slots').removeClass('error');
   $('#loading:hidden').show();
   return true;
}

function __process_submission(res) {
    
   // make sure any error messages are hidden
   $('div.error:visible').hide();
   // and the exmaple
   $('#for-example:visible').remove();
   

   __update_document_title(res.match_text);
   //if (res.word_count>=1) 
   //  $('#matches').text(res.match_text);
   if (!res.word_count) 
     $('#matches:hidden').show().text(res.match_text);
   else
     $('#matches:visible').hide();
   
   if (res.alternatives_truncated)
     $('#Results').attr('title', 'Results (truncated)');
   else
     $('#Results').attr('title', 'Results ('+res.word_count+')');
   
   $('li', '#Results').remove();
   $('div.definition').remove();
   var all, w;
   var wrapped;
   if (res.word_count) {
      $.each(res.words, function(i,r) {
         if (r.definition) {
            all = $('<a href="#definition_'+ __word2id(r.word) +'"></a>');
            __make_definition_section(r.word, r.definition);
         }
         else
           all = $('<span class="word"></span>');
         e = r.word;
         for (var i=0, len=e.length; i<len; i++) {
            if (res.match_points[i])
              all.append($('<span class="match letter"></span>').text(e.charAt(i)));
            else
              all.append($('<span class="letter"></span>').text(e.charAt(i)));
         }
         if (r.by_clue)
           all.append($('<span class="by_clue"></span>').text('~ ' + r.by_clue));
         //if (r.definition)
         //  all.append($('<em class="definition"></em>').text(r.definition));
         wrapped = $('<li></li>');
         if (!r.definition) wrapped.addClass('nolink');
         
         wrapped.append(all);
         $('#Results').append(wrapped);
      });
      showPage($('#Results')[0], 0);
   } else {
      $('#matches').text(res.match_text);
   }
   $('#loading:visible').hide();
   
   $('#clear-search').show();
   __done_search = true;
   
}

function __make_definition_section(word, definition) {
   var id = __word2id(word);
   id = 'definition_' + id;
   var c = $('<div></div>').addClass('definition').attr('parentName', "Results").attr('id', id).attr('title', word);
   c.append($('<h2></h2>').text('Definition:'));
   var ul = $('<ul></ul>');
   ul.append($('<li></li>').text(definition));
   c.append(ul);
   $('body').append(c);
   
}

function __error_ajaxSubmit(request, response_text) {
   $('#error__ajax').show();
   $('#error__ajax .response').text(response_text);
}

var submit_options = {
   url: '/simple/json/',
     type: 'GET',
     dataType: 'json',
     error: __error_ajaxSubmit,
     beforeSubmit: __before_ajaxSubmit,
     success: __process_submission
};
   

function ajaxSearch() {
  $('form#simple').ajaxSubmit(submit_options);
  return false;
}


var orig_document_title;
$(function() {
  
   $('#id_slots').bind('keyup', function() {
      this.value = __clean_slots(this.value);
   });
   if (!$('#id_slots').val())
     $('#id_slots')[0].focus();
   
   if ($('#match_text').text())
     __update_document_title($('#match_text').text());
    
   
   orig_document_title = document.title;
  
});

