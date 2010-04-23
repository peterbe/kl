
/* SPARKLINES
---------------------------------------------------------------------- */
function sparklines_init() {
   $.getJSON('/get_sparklines.json', function(res) {
     $('#sparklines-outer').append(
      $('<a></a>').attr('href',res.href).attr('title', res.alt).append(
         $('<img>').attr('src', res.src).attr('alt', res.alt)));
   });
}

/* FEEDBACK
---------------------------------------------------------------------- */
function feedback_init() {
  var form = $('#feedback');
  var textarea = form.find('#id_feedback');
  var default_value = textarea.val();
  var submit = form.find('.submit');
  var table = form.find('table');

  textarea.height(20);
  submit.hide();
  
  textarea.click(function(e) {
    if (textarea.height() < 50) {
      textarea.height(100).val('');
      submit.show();
      table.show();
      __answer_quiz();
    }
  });
  
  form.find('.alt_button').click(function(e) {
    e.preventDefault();
    textarea.height(20).val(default_value);
    submit.hide();
    table.hide();
  });
   
   // HP
   form.bind('mouseover', function() {
      $('#your-website-inp').hide();
      form.unbind('mouseover');
   });
}

function __answer_quiz() {
   var question = $('#quiz_question').text();
   $.getJSON('/quiz_answer.json', {question:question}, function(res) {
      if (res && res.answer) {
         $('input[name="quiz_answer"]').val(res.answer);
         $('tr#quiz').hide();
         
      }
   });
}

/* INIT
---------------------------------------------------------------------- */
$(function() {
   feedback_init();
   
   if (typeof SPARKLINES != "undefined")
     sparklines_init();
});