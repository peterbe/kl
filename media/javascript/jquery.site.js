/* SETTINGS
---------------------------------------------------------------------- */
function settings_init() {
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



/* INIT
---------------------------------------------------------------------- */
$(function() {
  feedback_init();
  
});