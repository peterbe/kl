/**
 * @author mmalone
 */
// used by the incremental list loading Sample
var controller = null;
function insertProgress()
{
	var progContainer = document.getElementById("progressCont");
	var can = document.createElement("canvas");
	can.setAttribute("height", 100);
	can.setAttribute("width", 100);
	can.setAttribute("style", "background:#transparent;");
	progContainer.appendChild(can);

	controller = getLoading(can.getContext("2d"), 12, {x:20, y:20}, 6, {width: 2, height: 5}, {red: 50, green: 79, blue: 133});
}
// used by the toggle button in the button samples
function toggleBtn(which)
{
	which.className = (which.className.indexOf('togButtonOff') > 0) ? 'togButton togButtonOn noHighlight' : 'togButton togButtonOff noHighlight';
}

var startDate = null;

// used by the window sample
var win = null;
function showChild() {
	
	var loc = "child.html";	
	var winStr = "resizable=1,status=yes,scrollbars=yes,toolbar=no,location=no,menu=no";
	var winName = "iPhone";
	win = window.open(loc, winName , winStr);
}

// used by the window sample
function windowCheck() {
	try 
	{
		if(!win.name) {
			alert("Child is Closed");	
			return false;
		}
	}
	catch(e) {
		alert("Child is Closed");	
		return false;
	}
	return true;
}

