
var animateX = -20;
var animateInterval = 24;

var currentPage = null;
var currentDialog = null;
var currentWidth = 0;
var currentHash = location.hash;
var hashPrefix = "#_";
var pageHistory = [];

addEventListener("load", function(event)
{
    var body = document.getElementsByTagName("body")[0];
    for (var child = body.firstChild; child; child = child.nextSibling)
    {
        if (child.nodeType == 1 && child.getAttribute("selected") == "true")
        {
            showPage(child);
            break;
        }
    }

    setInterval(checkOrientAndLocation, 300);
   
    // Comment out when in dev/debug mode
    setTimeout(hideAddress, 100);
}, false);

function hideAddress() {

	window.scrollTo(0, 1); // pan to the bottom, hides the location bar
}

addEventListener("click", function(event)
{
   var link = event.target;
   if (link && (!link.hash || link.hash=='#')) return true;
   
   event.preventDefault();

   while (link && link.localName && link.localName.toLowerCase() != "a")
     link = link.parentNode;
   
   if (link && link.localName && link.hash)
     {
        var page = document.getElementById(link.hash.substr(1));
        showPage(page);
     }
}, true);


function checkOrientAndLocation() {
   if (window.innerWidth != currentWidth) {
      currentWidth = window.innerWidth;
      
      var orient = innerWidth == 320 ? "portrait" : "landscape";
      if (orient == "portrait")
        $('#id_slots').css('width', '200px');
      else
        $('#id_slots').css('width', '300px');

      document.body.setAttribute("orient", orient);
      setTimeout(hideAddress, 100);
      
   }
}
   
    
function showPage(page, backwards)
{
   
   if(page == null) { return;}
    if (currentDialog)
    {
        currentDialog.removeAttribute("selected");
        currentDialog = null;
    }

    if (page.className.indexOf("dialog") != -1)
    {
        showDialog(page);
    }
    else
    {        
        location.href = currentHash = hashPrefix + page.id;
        pageHistory.push(page.id);

        var fromPage = currentPage;
        currentPage = page;

        var pageTitle = document.getElementById("pageTitle");
        pageTitle.innerHTML = page.title || "";

        var homeButton = document.getElementById("homeButton");
        if (homeButton)
        {
            homeButton.style.display = (page.id) == "XXX" ? "none" : "inline";
            var parentName = page.getAttribute("parentName");
           if(parentName != undefined)
            {
            	homeButton.innerHTML = parentName || "";
            	homeButton.href="#"+parentName;
            }
           else 
             {
                homeButton.innerHTML = "Exit";
                homeButton.href="..";
             }
        }
        if(fromPage) 
        {
            setTimeout(swipePage, 0, fromPage, page, backwards);
         }
    }
}

function swipePage(fromPage, toPage, backwards)
{        
    toPage.style.left = "100%";
    toPage.setAttribute("selected", "true");
    scrollTo(0, 1);

    var percent = 100;
    var timer = setInterval(function()
    {
        percent += animateX;
        if (percent <= 0)
        {
            percent = 0;
            fromPage.removeAttribute("selected");
            clearInterval(timer);
        }

        fromPage.style.left = (backwards ? (100-percent) : (percent-100)) + "%"; 
        toPage.style.left = (backwards ? -percent : percent) + "%"; 
    }, animateInterval);
}

function showDialog(form)
{
    currentDialog = form;
    form.setAttribute("selected", "true");
    
    form.onsubmit = function(event)
    {
        event.preventDefault();
        form.removeAttribute("selected");

        var index = form.action.lastIndexOf("#");
        if (index != -1)
            showPage(document.getElementById(form.action.substr(index+1)));
    }

    form.onclick = function(event)
    {
        if (event.target == form)
            form.removeAttribute("selected");
    }
}

