# -*- coding: utf-8 -*-
import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>Thông báo Đăng ký Môn học Học kỳ 1 Năm học 2026-2027</title>
  <style>
    @page {
      size: A4;
      margin: 12mm 12mm 12mm 18mm;
    }
    body {
      font-family: "Times New Roman", "Liberation Serif", serif;
      font-size: 11pt;
      line-height: 1.3;
      color: #000;
      margin: 0;
      padding: 0;
    }
    .doc-header {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 10px;
    }
    .doc-header td {
      vertical-align: top;
      padding: 0;
    }
    .doc-header-left {
      width: 45%;
      text-align: center;
    }
    .doc-header-right {
      width: 55%;
      text-align: center;
    }
    .institution-name {
      font-weight: bold;
      font-size: 9.5pt;
      text-transform: uppercase;
    }
    .sub-institution {
      font-size: 10pt;
      font-weight: bold;
    }
    .doc-number {
      font-size: 9.5pt;
      margin-top: 3px;
    }
    .national-title {
      font-weight: bold;
      font-size: 10.5pt;
      text-transform: uppercase;
    }
    .national-subtitle {
      font-weight: bold;
      font-size: 11.5pt;
      margin-top: 1px;
    }
    .doc-date {
      font-style: italic;
      font-size: 10.5pt;
      margin-top: 6px;
    }
    .divider {
      width: 35%;
      border-top: 1px solid #000;
      margin: 3px auto 0 auto;
    }
    .divider-right {
      width: 45%;
      border-top: 1px solid #000;
      margin: 3px auto 0 auto;
    }
    .doc-title-container {
      text-align: center;
      margin-bottom: 10px;
      margin-top: 3px;
    }
    .doc-title {
      font-weight: bold;
      font-size: 12.5pt;
      text-transform: uppercase;
      margin: 0;
    }
    .doc-subtitle {
      font-weight: bold;
      font-size: 10.5pt;
      margin: 4px 0 0 0;
      text-align: center;
      line-height: 1.25;
    }
    .doc-body {
      text-align: justify;
    }
    .pursuant {
      font-style: italic;
      margin-bottom: 5px;
      padding-left: 20px;
      text-indent: -20px;
      font-size: 10pt;
    }
    .section-title {
      font-weight: bold;
      margin-top: 10px;
      margin-bottom: 4px;
      font-size: 11pt;
    }
    .section-content {
      margin-bottom: 6px;
      text-indent: 1cm;
    }
    .no-indent {
      text-indent: 0 !important;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0;
      font-size: 10pt;
      page-break-inside: avoid;
    }
    table.data-table th, table.data-table td {
      border: 1px solid #000;
      padding: 4px 5px;
      vertical-align: top;
      line-height: 1.2;
    }
    table.data-table th {
      font-weight: bold;
      text-align: center;
      background-color: #f2f2f2;
    }
    .bullet-list {
      margin-top: 3px;
      margin-bottom: 3px;
      padding-left: 20px;
    }
    .bullet-list li {
      margin-bottom: 3px;
      text-align: justify;
    }
    .footer-section {
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
      page-break-inside: avoid;
    }
    .footer-section td {
      vertical-align: top;
      padding: 0;
    }
    .recipients {
      width: 40%;
      font-size: 8.5pt;
      line-height: 1.2;
    }
    .recipients-title {
      font-weight: bold;
      font-style: italic;
    }
    .signatory {
      width: 60%;
      text-align: center;
    }
    .signatory-title {
      font-weight: bold;
      text-transform: uppercase;
      font-size: 10pt;
    }
    .signatory-subtitle {
      font-weight: bold;
      font-size: 10pt;
      margin-top: 1px;
    }
    .signatory-name {
      font-weight: bold;
      margin-top: 50px;
      font-size: 11pt;
    }
    .page-break {
      page-break-before: always;
    }
    .table-title {
      font-weight: bold;
      margin-top: 6px;
      margin-bottom: 3px;
      font-size: 10.5pt;
    }
  </style>
</head>
<body>

  <table class="doc-header">
    <tr>
      <td class="doc-header-left">
        <span class="institution-name">NGÂN HÀNG NHÀ NƯỚC VIỆT NAM</span><br>
        <span class="sub-institution">TRƯỜNG ĐẠI HỌC NGÂN HÀNG<br>THÀNH PHỐ HỒ CHÍ MINH</span>
        <div class="divider"></div>
        <div class="doc-number">Số: 1041/QĐ-ĐHNH</div>
      </td>
      <td class="doc-header-right">
        <span class="national-title">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</span><br>
        <span class="national-subtitle">Độc lập - Tự do - Hạnh phúc</span>
        <div class="divider-right"></div>
        <div class="doc-date">TP. Hồ Chí Minh, ngày 26 tháng 6 năm 2026</div>
      </td>
    </tr>
  </table>

  <div class="doc-title-container">
    <h1 class="doc-title">THÔNG BÁO</h1>
    <div class="doc-subtitle">Về việc Đăng ký môn học Học kỳ 1, Năm học 2026–2027 cho Sinh viên Đại học Chính quy Chương trình giảng dạy một phần bằng tiếng Anh, Chương trình Đào tạo Đặc biệt và Chương trình Cử nhân Tài năng (Honors Program)</div>
  </div>

  <div class="doc-body">
    <div class="pursuant">Căn cứ Quyết định số 1577/QĐ-ĐHNH ngày 31 tháng 8 năm 2021 của Hiệu trưởng về việc sửa đổi, bổ sung một số điều của Quy chế quản lý học vụ đối với chương trình đào tạo đại học chính quy chất lượng cao tại Trường Đại học Ngân hàng TP. Hồ Chí Minh ban hành kèm theo Quyết định số 2134A/QĐ-ĐHNH ngày 02 tháng 10 năm 2017;</div>
    <div class="pursuant">Căn cứ Quyết định số 466/QĐ-ĐHNH ngày 28 tháng 2 năm 2024 của Hiệu trưởng về việc ban hành Quy chế tổ chức và quản lý đào tạo đại học tại Trường Đại học Ngân hàng TP. Hồ Chí Minh;</div>
    <div class="pursuant">Căn cứ Quyết định số 1070/QĐ-ĐHNH ngày 24 tháng 4 năm 2024 của Hiệu trưởng về việc ban hành Quy định về tổ chức và thực hiện chương trình đào tạo chất lượng cao, chương trình đào tạo một phần bằng tiếng Anh, và chương trình đào tạo đặc biệt trình độ đại học tại Trường Đại học Ngân hàng TP. Hồ Chí Minh;</div>
    <div class="pursuant">Căn cứ Quyết định số 1076/QĐ-ĐHNH ngày 08 tháng 5 năm 2019 của Hiệu trưởng về việc ban hành "Quy định về việc đăng ký và rút bớt môn học theo hệ thống đào tạo tín chỉ tại Trường Đại học Ngân hàng TP. Hồ Chí Minh";</div>

    <div class="section-content no-indent" style="margin-top: 10px;">
      Phòng Đào tạo thông báo đến sinh viên hệ đại học chính quy Chương trình giảng dạy một phần bằng tiếng Anh, Chương trình Đào tạo Đặc biệt và Chương trình Cử nhân Tài năng kế hoạch và quy định đăng ký môn học Học kỳ 1, Năm học 2026–2027 như sau:
    </div>

    <div class="section-title">1. Khung Kế hoạch Học tập</div>
    <div class="section-content">
      Học kỳ 1 năm học 2026–2027 sẽ bắt đầu từ Tuần 1 và kết thúc vào Tuần 22. Tuần 1 chính thức bắt đầu từ Thứ Năm, ngày 03 tháng 9 năm 2026.
    </div>

    <div class="section-title">2. Công bố Thời khóa biểu học và Lịch thi</div>
    <div class="section-content">
      Thời khóa biểu học và lịch thi học kỳ 1 năm học 2026–2027 đối với sinh viên đại học chính quy Chương trình giảng dạy một phần bằng tiếng Anh sẽ được công bố trên các trang web: <a href="https://hub.edu.vn">https://hub.edu.vn</a> hoặc <a href="https://phongdaotao.hub.edu.vn">https://phongdaotao.hub.edu.vn</a> (Mục: Thông báo) vào ngày 29 tháng 6 năm 2026.
    </div>

    <div class="section-title">3. Đăng ký Môn học (3 Giai đoạn)</div>
    
    <div class="section-title" style="padding-left: 15px; font-weight: normal; font-style: italic;">3.1. Giai đoạn 1 – Đăng ký Chính thức</div>

    <div class="table-title">A. Khóa 13 (K13), Chương trình Đào tạo Đặc biệt – Khóa 2 (STP Khóa 2)</div>
    
    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt;">A.1. Đăng ký theo Lớp/Nhóm (K13 Nhóm 1, 2, 3, …)</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Nhóm đăng ký tương ứng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>- Kinh tế Quốc tế<br>- Hệ thống Thông tin Quản lý<br>- Luật Kinh tế<br>- Chương trình Đặc biệt (Ngành Ngôn ngữ Anh)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 06/07/2026<br>đến 16:00 ngày 07/07/2026</td>
          <td>- K13 Nhóm KTQT 01 đến Nhóm KTQT 02<br>- K13 Nhóm HTTT 01 đến Nhóm HTTT 02<br>- K13 Nhóm LKT 01 đến Nhóm LKT 03<br>- K2 Nhóm NNA 01 đến Nhóm NNA 02</td>
        </tr>
        <tr>
          <td>- Quản trị Kinh doanh</td>
          <td style="text-align: center; vertical-align: middle;">Từ 19:00 ngày 07/07/2026<br>đến 16:00 ngày 08/07/2026</td>
          <td>K13 Nhóm QTKD 01 đến Nhóm QTKD 09</td>
        </tr>
        <tr>
          <td>- Kế toán</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 07/07/2026<br>đến 16:00 ngày 08/07/2026</td>
          <td>K13 Nhóm KT01 đến Nhóm KT 07</td>
        </tr>
        <tr>
          <td>- Tài chính - Ngân hàng</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 08/07/2026<br>đến 16:00 ngày 09/07/2026</td>
          <td>K13 Nhóm TCNH 01 đến Nhóm TCNH 31</td>
        </tr>
      </tbody>
    </table>

    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt; margin-top: 10px;">A.2. Đăng ký riêng từng môn học/học phần (bao gồm Giáo dục Thể chất 3, Tiếng Anh tăng cường 4 và 5, Kỹ năng mềm, môn giáo dục đại cương, môn tự chọn theo định hướng chuyên ngành, v.v.)</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Ghi chú quan trọng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tài chính - Ngân hàng, Kế toán, Hệ thống thông tin quản lý (MIS), Kinh tế quốc tế, Luật kinh tế, Ngôn ngữ Anh (Chuyên ngành)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:00 ngày 13/07/2026<br>đến 16:00 ngày 14/07/2026</td>
          <td><strong>Chỉ đăng ký môn học riêng lẻ.</strong><br>Trong giai đoạn đăng ký môn tự chọn, Tin học ứng dụng, GDTC 3, Kỹ năng mềm, và Tiếng Anh tăng cường 4 & 5, hệ thống chỉ hiển thị các môn này và không hiển thị môn bắt buộc. Sinh viên tuyệt đối không hủy kết quả đăng ký của các môn bắt buộc đã đăng ký thành công trước đó.</td>
        </tr>
      </tbody>
    </table>

    <div class="table-title">B. Khóa 12 (K12), Chương trình Đào tạo Đặc biệt – Khóa 1 (STP Khóa 1)</div>
    
    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt;">B.1. Đăng ký theo Nhóm/Lớp (K12 Nhóm 1, 2, 3, …)</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Nhóm đăng ký tương ứng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>- Kinh tế Quốc tế<br>- Hệ thống Thông tin Quản lý<br>- Chương trình Đặc biệt (Ngành Ngôn ngữ Anh)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:00 ngày 14/07/2026<br>đến 21:00 ngày 14/07/2026</td>
          <td>- K12 Nhóm KTQT 01 đến Nhóm KTQT 02<br>- K12 Nhóm HTTT 01 đến Nhóm HTTT 02<br>- K1 Nhóm NNA 01 đến Nhóm NNA 02</td>
        </tr>
        <tr>
          <td>- Quản trị Kinh doanh</td>
          <td style="text-align: center; vertical-align: middle;">Từ 21:00 ngày 14/07/2026<br>đến 16:00 ngày 15/07/2026</td>
          <td>K12 Nhóm QTKD 01 đến Nhóm QTKD 09</td>
        </tr>
        <tr>
          <td>- Kế toán</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:00 ngày 15/07/2026<br>đến 21:00 ngày 15/07/2026</td>
          <td>K12 Nhóm KT01 đến Nhóm KT06</td>
        </tr>
        <tr>
          <td>- Tài chính - Ngân hàng</td>
          <td style="text-align: center; vertical-align: middle;">Từ 21:00 ngày 15/07/2026<br>đến 16:00 ngày 16/07/2026</td>
          <td>K12 Nhóm TCNH 01 đến Nhóm TCNH 28</td>
        </tr>
      </tbody>
    </table>

    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt; margin-top: 10px;">B.2. Đăng ký riêng từng môn học/học phần (bao gồm Giáo dục Thể chất 4, Tiếng Anh chuyên ngành (ESP), Kỹ năng mềm, môn giáo dục đại cương, môn tự chọn theo định hướng chuyên ngành, v.v.)</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Ghi chú quan trọng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tài chính - Ngân hàng, Kế toán, Hệ thống thông tin quản lý (MIS), Kinh tế quốc tế, Ngôn ngữ Anh (Chuyên ngành)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:00 ngày 16/07/2026<br>đến 16:00 ngày 17/07/2026</td>
          <td><strong>Chỉ đăng ký môn học riêng lẻ.</strong><br>Trong giai đoạn đăng ký môn tự chọn, Tiếng Anh chuyên ngành (ESP), Tin học ứng dụng, và GDTC 4, hệ thống chỉ hiển thị các môn này và không hiển thị môn bắt buộc. Sinh viên tuyệt đối không hủy kết quả đăng ký của các môn bắt buộc đã đăng ký thành công trước đó.</td>
        </tr>
      </tbody>
    </table>

    <div class="table-title" style="margin-top: 15px;">C. Khóa 11 trở về trước</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Ghi chú</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tài chính - Ngân hàng, Kế toán, Quản trị Kinh doanh</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:30 ngày 17/07/2026<br>đến 07:00 ngày 20/07/2026<br><span style="font-size: 9.5pt; color: #555;">(Lưu ý: Bản gốc tiếng Anh ghi ngày 27/07/2026)</span></td>
          <td><strong>Chỉ đăng ký theo môn học.</strong></td>
        </tr>
      </tbody>
    </table>

    <div class="table-title" style="margin-top: 15px;">D. Khóa 1 – Chương trình Cử nhân Tài năng (Honors Program)</div>
    
    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt;">D.1. Đăng ký theo Nhóm/Lớp</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Nhóm đăng ký tương ứng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tài chính - Ngân hàng</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 20/07/2026<br>đến 11:00 ngày 21/07/2026</td>
          <td>K1 Nhóm TCNH 01 đến Nhóm TCNH 02</td>
        </tr>
      </tbody>
    </table>

    <div style="font-weight: bold; margin-left: 10px; font-size: 10.5pt; margin-top: 10px;">D.2. Đăng ký riêng từng môn học/học phần (bao gồm Giáo dục Thể chất, Kỹ năng mềm, và môn giáo dục đại cương)</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 30%;">Ngành</th>
          <th style="width: 35%;">Thời gian đăng ký<br>(trên hệ thống http://online.hub.edu.vn)</th>
          <th style="width: 35%;">Ghi chú</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tài chính - Ngân hàng</td>
          <td style="text-align: center; vertical-align: middle;">Từ 13:00 ngày 21/07/2026<br>đến 16:00 ngày 21/07/2026</td>
          <td><strong>Chỉ đăng ký theo môn học.</strong></td>
        </tr>
      </tbody>
    </table>

    <div class="section-content no-indent" style="margin-top: 12px; font-style: italic;">
      (i) Sau khi kết thúc thời hạn đăng ký môn học Giai đoạn 1, Phòng Đào tạo sẽ công bố danh sách các môn học bị hủy do không đủ số lượng đăng ký tối thiểu vào ngày 24 tháng 7 năm 2025 (nguyên văn), tại trang web: <a href="https://clc.hub.edu.vn/">https://clc.hub.edu.vn/</a> mục Thông báo.<br>
      (ii) Phòng Đào tạo sẽ tiếp nhận yêu cầu của sinh viên về việc mở thêm lớp môn học (nếu có) từ ngày 10/07/2026 đến trước 08:00 ngày 13/07/2025 (nguyên văn). Sinh viên gửi yêu cầu qua biểu mẫu trực tuyến tại liên kết: <a href="https://forms.gle/XqTfXPJ8jXFiyfsV8">https://forms.gle/XqTfXPJ8jXFiyfsV8</a>
    </div>

    <div class="section-title" style="padding-left: 15px; font-weight: normal; font-style: italic;">3.2. Giai đoạn 2 – Đăng ký Bổ sung</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 40%;">Đối tượng học sinh/sinh viên</th>
          <th style="width: 60%;">Thời gian đăng ký (trên hệ thống http://online.hub.edu.vn)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Khóa 13 & Chương trình Đào tạo Đặc biệt Khóa 2 (STP Khóa 2)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 21/07/2026 đến 16:00 ngày 22/07/2026</td>
        </tr>
        <tr>
          <td>Khóa 12 & Chương trình Đào tạo Đặc biệt Khóa 1 (STP Khóa 1)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 20:00 ngày 22/07/2026 đến 16:00 ngày 23/07/2026</td>
        </tr>
        <tr>
          <td>Khóa 1 – Chương trình Cử nhân Tài năng (Honors Program)</td>
          <td style="text-align: center; vertical-align: middle;">Từ 18:00 ngày 23/07/2026 đến 21:00 ngày 23/07/2026</td>
        </tr>
        <tr>
          <td>Khóa 11 trở về trước</td>
          <td style="text-align: center; vertical-align: middle;">Từ 21:00 ngày 23/07/2026 đến 15:00 ngày 24/07/2026</td>
        </tr>
      </tbody>
    </table>
    <div class="section-content no-indent" style="font-style: italic; margin-top: 5px;">
      Lưu ý: Sau khi kết thúc thời hạn đăng ký môn học Giai đoạn 2, Phòng Đào tạo sẽ công bố danh sách các môn học bị hủy do không đạt số lượng đăng ký tối thiểu vào ngày 30 tháng 7 năm 2025 (nguyên văn), tại trang web: <a href="http://online.hub.edu.vn/">http://online.hub.edu.vn/</a> mục Thông báo.
    </div>

    <div class="section-title" style="padding-left: 15px; font-weight: normal; font-style: italic;">3.3. Giai đoạn 3 – Đăng ký Thêm</div>
    <ul class="bullet-list">
      <li><strong>Thời gian:</strong> Từ ngày 03 tháng 9 năm 2026 đến hết ngày 09 tháng 9 năm 2026.</li>
      <li><strong>Phương thức:</strong> Đăng ký trực tuyến đối với các môn học còn chỗ trống. Trong Giai đoạn 3, sinh viên không được phép rút bớt các môn học đã đăng ký.</li>
      <li><strong>Học phí:</strong> Sinh viên phải hoàn thành đóng học phí cho tất cả các môn đăng ký thêm trong Giai đoạn 3 ngay trong ngày đăng ký.</li>
    </ul>

    <div class="section-title">4. Thời hạn và Phương thức Nộp Học phí</div>
    <ul class="bullet-list">
      <li><strong>Thời gian đóng học phí:</strong> Từ ngày 27 tháng 7 năm 2026 đến hết ngày 09 tháng 8 năm 2026.</li>
      <li><strong>Phương thức thanh toán:</strong> Sinh viên truy cập cổng thanh toán trực tuyến của Trường Đại học Ngân hàng TP. Hồ Chí Minh tại địa chỉ <a href="https://e-bills.vn/pay/hub">https://e-bills.vn/pay/hub</a> để kiểm tra công nợ học phí và thực hiện thanh toán qua ứng dụng VCB Digibank, ứng dụng mobile banking của các ngân hàng khác, hoặc ví điện tử. (Hướng dẫn sử dụng hệ thống thanh toán trực tuyến của trường có tại: <a href="https://e-bills.vn/pay/hub">https://e-bills.vn/pay/hub</a>).</li>
    </ul>

    <div class="section-title">5. Xác nhận Kết quả Đăng ký Môn học</div>
    <ul class="bullet-list">
      <li>Sinh viên phải xác nhận kết quả đăng ký môn học và phản hồi lỗi (nếu có) trong giờ hành chính ngày 18–19 tháng 8 năm 2025 (nguyên văn).</li>
      <li>Sau thời hạn này, Phòng Đào tạo sẽ không giải quyết bất kỳ khiếu nại hoặc điều chỉnh nào liên quan đến việc đăng ký môn học.</li>
    </ul>

    <div class="section-title">6. Các Lưu ý Quan trọng Về Đăng ký Môn học</div>
    <div class="section-content no-indent">
      Để đảm bảo đăng ký môn học chính xác và hiệu quả, sinh viên bắt buộc phải đọc kỹ và tuân thủ các quy định và hướng dẫn sau đây:
    </div>
    <ul class="bullet-list">
      <li>Thời khóa biểu học và thi Học kỳ 1 năm học 2026–2027 đối với chương trình giảng dạy một phần bằng tiếng Anh được xây dựng cụ thể theo từng khóa (Khóa 12 và 13), ngành học (Tài chính - Ngân hàng, Kế toán, Quản trị Kinh doanh, Hệ thống Thông tin Quản lý, Kinh tế Quốc tế, Ngôn ngữ Anh), môn tự chọn theo định hướng và cơ sở học (Cơ sở Sài Gòn và Cơ sở Thủ Đức). Sinh viên phải xem xét kỹ các thời khóa biểu này trước khi đăng ký.</li>
      <li>Đối với các môn học tự chọn, sinh viên phải chọn đúng các môn học phù hợp với định hướng học tập của mình.</li>
      <li>Sinh viên chỉ được phép đăng ký các môn học được thiết kế cho ngành học của mình. Ví dụ: Sinh viên ngành Tài chính - Ngân hàng Khóa 11 không được đăng ký các môn học dành cho sinh viên Kế toán hoặc Quản trị Kinh doanh Khóa 11, và ngược lại.</li>
      <li>Sinh viên phải nắm rõ chương trình học của mình, đặc biệt là các yêu cầu về môn học tiên quyết. Khuyến khích đăng ký các môn học tiên quyết trước các môn học có liên quan khác.</li>
      <li>Sinh viên phải đăng ký khối lượng học tập tuân thủ yêu cầu về số tín chỉ tối thiểu và tối đa được quy định trong Quy chế Học vụ hiện hành, cụ thể như sau:
        <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px;">
          <li>Khối lượng học tập tối thiểu phải đạt ít nhất hai phần ba (2/3) khối lượng học tập trung bình của một học kỳ theo kế hoạch học tập mẫu.</li>
          <li>Khối lượng học tập tối đa không được vượt quá một phần rưỡi (3/2) khối lượng học tập trung bình của một học kỳ theo kế hoạch học tập mẫu.</li>
          <li>Đối với sinh viên học cùng lúc hai chương trình đào tạo, giới hạn khối lượng học tập tối đa trong học kỳ không áp dụng.</li>
          <li>Các môn học/học phần đặc biệt không được tính vào khối lượng học tập tối thiểu hoặc tối đa.</li>
          <li>Để được xét học bổng trong học kỳ bình thường, sinh viên phải đăng ký khối lượng học tập tối thiểu là 15 tín chỉ.</li>
        </ul>
      </li>
      <li>Sinh viên từ Khóa K12 trở đi chưa hoàn thành chuẩn đầu vào tiếng Anh và công nghệ thông tin theo quy định tại Quyết định số 894/QĐ-ĐHNH ngày 04 tháng 4 năm 2025 về Chuẩn năng lực Công nghệ thông tin và Thông báo số 715/TB-ĐHNH ngày 15 tháng 5 năm 2026 về Phụ lục Chuẩn năng lực Tiếng Anh và Công nghệ thông tin đối với sinh viên đại học tại Trường Đại học Ngân hàng TP. Hồ Chí Minh sẽ bị giới hạn số tín chỉ đăng ký học kỳ theo quy định của Nhà trường.</li>
      <li>Sinh viên đăng ký ít hơn số tín chỉ tối thiểu hoặc không đăng ký môn học nào sẽ bị cảnh báo học tập theo quy định của trường.</li>
      <li>Sinh viên nên lưu giữ bản in xác nhận đăng ký môn học để đối chiếu khi có vấn đề phát sinh.</li>
      <li>Sinh viên phải theo dõi thông báo đóng học phí từ Phòng Tài chính – Kế toán để đảm bảo đóng học phí đúng hạn.
        <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px;">
          <li>Sinh viên không đóng học phí đúng hạn sẽ không có tên chính thức trong danh sách các lớp học đã đăng ký trong Học kỳ 1 năm học 2026–2027.</li>
          <li>Để được hỗ trợ, sinh viên có thể liên hệ Văn phòng Phòng Đào tạo – Bộ phận Quản lý Chương trình Tiếng Anh CTĐ, email: <a href="mailto:ctchatluongcao@hub.edu.vn">ctchatluongcao@hub.edu.vn</a>, Điện thoại: 02838971638 – 02838212430.</li>
        </ul>
      </li>
    </ul>

    <div style="font-weight: bold; margin-top: 15px; margin-bottom: 5px;">- Thông tin liên hệ hỗ trợ theo từng khóa:</div>
    <ul class="bullet-list">
      <li><strong>Khóa 9, 12 & Khóa 1 – Chương trình Đặc biệt:</strong> Thầy Quân Minh – Điện thoại: (0908.184.190), Email: <a href="mailto:minhtq@hub.edu.vn">minhtq@hub.edu.vn</a></li>
      <li><strong>Khóa 10 & Khóa 2 – Chương trình Đặc biệt:</strong> Cô Mỹ Hạnh – Điện thoại: (0932.692.039), Email: <a href="mailto:hanhptm@hub.edu.vn">hanhptm@hub.edu.vn</a></li>
      <li><strong>Khóa 1 Chương trình Cử nhân Tài năng (Honors Program):</strong> Cô Nhựt Pil – Điện thoại: (+84) 939 852 960, Email: <a href="mailto:pilln@hub.edu.vn">pilln@hub.edu.vn</a></li>
      <li><strong>Khóa 11 trở về trước:</strong> Thầy Việt Phương – Điện thoại: (0903.831.866), Email: <a href="mailto:phuonglv@hub.edu.vn">phuonglv@hub.edu.vn</a></li>
    </ul>

    <table class="footer-section">
      <tr>
        <td class="recipients">
          <span class="recipients-title">Nơi nhận:</span><br>
          – Ban Giám hiệu (để báo cáo);<br>
          – Các Khoa (để phối hợp và phổ biến cho sinh viên);<br>
          – Các Phòng & Trung tâm: Phòng Tài chính - Kế toán (FAD), Phòng Khảo thí & Đảm bảo chất lượng (TQAD), Trung tâm CNTT & Dữ liệu (ITMD), SAC, SSC;<br>
          – Đoàn Thanh niên - Hội Sinh viên;<br>
          – Phòng Hành chính - Tổng hợp (để đăng website);<br>
          – Sinh viên (để thực hiện);<br>
          – Lưu: Văn thư, Phòng Đào tạo (DAA).
        </td>
        <td class="signatory">
          <span class="signatory-title">TL. HIỆU TRƯỞNG</span><br>
          <span class="signatory-subtitle">KT. TRƯỞNG PHÒNG<br>PHÓ TRƯỞNG PHÒNG</span><br>
          <span style="font-style: italic; font-size: 11pt; display: block; margin-top: 5px;">(Đã ký)</span>
          <div class="signatory-name">Nguyễn Thị Huỳnh Uyên</div>
        </td>
      </tr>
    </table>

  </div>

</body>
</html>
"""

with open("announcement_vi.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Generated announcement_vi.html successfully.")

# Run Chrome to print to PDF
chrome_cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--print-to-pdf=20260629081451-10422026-1041-announcement-vi.pdf",
    "announcement_vi.html"
]

try:
    subprocess.run(chrome_cmd, check=True)
    print("Compiled 20260629081451-10422026-1041-announcement-vi.pdf successfully.")
except Exception as e:
    print(f"Error compiling PDF: {e}")
