/* SETTINGS
---------------------------------------------------------------------- */
function settings_init() {
}



/* FEEDBACK
---------------------------------------------------------------------- */
function feedback_init() {
  var form = $('.feedback_form');
  var textarea = form.find('#id_feedback');
  var default_value = textarea.val();
  var submit = form.find('.submit');
  
  textarea.height(20);
  submit.hide();
  
  textarea.click(function(e) {
    if (textarea.height() < 50) {
      textarea.height(100).val('');
      submit.show();
    }
  });
  
  form.find('.alt_button').click(function(e) {
    e.preventDefault();
    textarea.height(20).val(default_value);
    submit.hide();
  });

  form.submit(function(e) {
    e.preventDefault();
    var data = {'text': textarea.val(), 'source': form.find('#id_source').val()}
    $.post(form.attr('action'), data, function(response) {
      if (response.success) {
        textarea.height(20).val('Tack :)');
        submit.hide();
      }
    }, 'json');
  });
}


/* INIT
---------------------------------------------------------------------- */
$(function() {
  feedback_init();
  
  
});