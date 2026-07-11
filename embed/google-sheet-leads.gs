/**
 * Ask Neevu → Google Sheet lead capture.
 *
 * Paste this into your Google Sheet's Apps Script editor (Extensions → Apps
 * Script), then deploy it as a Web App (steps in EMBED_AND_DB.md). Each lead the
 * chatbot captures is appended as a row — and, optionally, emailed to you.
 *
 * 100% free: no third-party service, just Google Sheets + Apps Script.
 */

// OPTIONAL — to get an email on every new lead, put an address here (else leave "").
var NOTIFY_EMAIL = "";

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

    // Write a header row once.
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["Received", "Name", "Phone", "Programme", "Child age", "Message", "Source"]);
      sheet.setFrozenRows(1);
    }

    sheet.appendRow([
      new Date(),
      data.name || "",
      data.phone || "",
      data.programme || "",
      data.child_age || "",
      data.message || "",
      data.source || ""
    ]);

    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(
        NOTIFY_EMAIL,
        "New Ask Neevu lead: " + (data.name || "(no name)"),
        "Name: " + (data.name || "") +
        "\nPhone: " + (data.phone || "") +
        "\nProgramme: " + (data.programme || "") +
        "\nSource: " + (data.source || "")
      );
    }

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
