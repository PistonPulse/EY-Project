import React from 'react';
import { Download, X, Printer, Loader2 } from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import tataLogo from '../assets/Tata_Capital_Logo-01.jpg';

interface SanctionLetterProps {
    customerName: string;
    loanDetails: {
        amount: number;
        interest_rate: number;
        tenure_months: number;
        monthly_emi: number;
    };
    sessionId: string;
    onClose: () => void;
    autoDownload?: boolean;
}

export const SanctionLetter: React.FC<SanctionLetterProps> = ({ customerName, loanDetails, sessionId, onClose, autoDownload = false }) => {
    const currentDate = new Date().toLocaleDateString('en-IN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });

    const refNo = `TATA-PL-${Math.floor(100000 + Math.random() * 900000)}`;
    const city = "Mumbai, Maharashtra"; // Default or dynamic if available

    const [isDownloading, setIsDownloading] = React.useState(false);
    const [logoBase64, setLogoBase64] = React.useState<string>('');

    React.useEffect(() => {
        // Pre-load logo as Base64 to ensure it renders correctly in PDF
        const loadLogo = async () => {
            try {
                const response = await fetch(tataLogo);
                const blob = await response.blob();
                const reader = new FileReader();
                reader.onloadend = () => setLogoBase64(reader.result as string);
                reader.readAsDataURL(blob);
            } catch (error) {
                console.error('Failed to load local logo:', error);
            }
        };
        loadLogo();
    }, []);

    const handlePrint = () => {
        window.print();
    };

    const handleDownload = async () => {
        try {
            setIsDownloading(true);
            const element = document.getElementById('sanction-letter-content');
            if (!element) throw new Error('Sanction letter content not found');

            const canvas = await html2canvas(element, {
                scale: 2,
                logging: false,
                useCORS: true, // Handle images using CORS
                allowTaint: false, // DO NOT allow taint, or toDataURL will fail
                backgroundColor: '#ffffff',
                windowWidth: element.scrollWidth,
                windowHeight: element.scrollHeight,
                onclone: (doc) => {
                    const el = doc.getElementById('sanction-letter-content');
                    if (el) {
                        el.style.padding = '40px';
                        // Force layout recalculation
                        const images = el.getElementsByTagName('img');
                        for (let i = 0; i < images.length; i++) {
                            images[i].style.display = 'block';
                        }
                    }
                }
            });

            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF('p', 'mm', 'a4');
            const imgWidth = 210;
            const pageHeight = 297;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;
            let heightLeft = imgHeight;
            let position = 0;

            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;

            while (heightLeft >= 0) {
                position = heightLeft - imgHeight; // position is negative offset
                pdf.addPage();
                pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
                heightLeft -= pageHeight;
            }

            // Upload to backend for sync
            try {
                const pdfBlob = pdf.output('blob');
                const formData = new FormData();
                formData.append('file', pdfBlob, 'sanction_letter.pdf');

                fetch(`http://localhost:8000/api/upload-sanction/${sessionId}`, {
                    method: 'POST',
                    body: formData
                }).catch(err => console.error('Background upload failed:', err));
            } catch (e) {
                console.error('Error preparing upload:', e);
            }

            pdf.save(`Sanction-Letter-${customerName.replace(/\s+/g, '-')}.pdf`);

            // If this was an auto-download triggered externally, close the modal immediately
            if (autoDownload) {
                onClose();
            }
        } catch (error: any) {
            console.error('Error generating PDF:', error);
            alert(`Failed to generate PDF: ${error.message || 'Unknown error'}. Please try printing instead.`);
        } finally {
            setIsDownloading(false);
        }
    };

    React.useEffect(() => {
        if (autoDownload && logoBase64) {
            // slight delay to ensure DOM is fully rendered before canvas capture
            const timer = setTimeout(() => {
                handleDownload();
            }, 500);
            return () => clearTimeout(timer);
        }
    }, [autoDownload, logoBase64]);

    return (
        <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 p-4 sm:p-6 backdrop-blur-sm print:bg-white print:p-0">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto print:shadow-none print:w-full print:max-w-none print:h-auto print:overflow-visible">

                {/* Modal Header - Hidden in Print */}
                <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between print:hidden z-10">
                    <h2 className="text-xl font-semibold text-gray-800">Sanction Letter</h2>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleDownload}
                            disabled={isDownloading}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isDownloading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            Download
                        </button>
                        <button
                            onClick={handlePrint}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            <Printer className="w-4 h-4" />
                            Print
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Letter Content - A4 Aspect Ratio Simulation */}
                <div id="sanction-letter-content" className="p-8 sm:p-12 text-sm text-gray-800 font-serif leading-relaxed print:p-0 print:text-xs bg-white">

                    {/* Header Section */}
                    <div className="flex justify-between items-start mb-8 border-b-2 border-red-700 pb-4">
                        <div className="flex flex-col">
                            {/* Logo - Base64 for reliable PDF generation */}
                            <img
                                src={logoBase64 || tataLogo}
                                alt="Tata Capital"
                                className="h-16 w-auto mb-2 object-contain"
                            />
                            <span className="text-xs text-gray-600 font-sans tracking-wide">We only do what's right for you</span>
                        </div>
                        <div className="text-right text-xs text-gray-600">
                            <p className="font-bold text-gray-800">Branch Office:</p>
                            <p>11th Floor, Tower A, Peninsula Business Park,</p>
                            <p>Ganpatrao Kadam Marg, Lower Parel,</p>
                            <p>Mumbai - 400013</p>
                        </div>
                    </div>

                    {/* Reference & Date */}
                    <div className="flex justify-between mb-6">
                        <div>
                            <p className="font-bold">Ref No: {refNo}</p>
                            <p className="font-bold">Date: {currentDate}</p>
                        </div>
                    </div>

                    {/* Borrower Details */}
                    <div className="mb-6">
                        <p className="font-bold">Name of the Borrower: {customerName.toUpperCase()}</p>
                        <p>Address: {city}</p>
                        <p>INDIA</p>
                    </div>

                    {/* Subject */}
                    <div className="mb-6">
                        <p>Dear Sir/Madam,</p>
                        <p className="text-center font-bold mt-4 underline underline-offset-2">
                            Sanction of Personal Loan facility of Rs. {loanDetails.amount.toLocaleString('en-IN')} under TATA PERSONAL LOAN SCHEME
                        </p>
                    </div>

                    {/* Body Paragraph */}
                    <div className="mb-6 text-justify">
                        <p className="mb-4">
                            In reference to your loan application dated {currentDate}, we are pleased to communicate our sanction of
                            Personal Loan of <strong>Rs. {loanDetails.amount.toLocaleString('en-IN')}</strong> (Rupees {convertNumberToWords(loanDetails.amount)} Only)
                            under <strong>TATA PERSONAL LOAN SCHEME</strong> on terms and conditions given here under and the
                            terms and conditions of the bank contained in the standard loan documents of the bank for such loans.
                        </p>
                        <p className="text-center font-bold">
                            You are requested to go through the terms & conditions of the sanction carefully.
                        </p>
                    </div>

                    {/* Terms Table */}
                    <div className="mb-8 border border-gray-300">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="bg-gray-100">
                                    <th className="border border-gray-300 px-3 py-2 text-left w-1/3 font-bold">Particulars</th>
                                    <th className="border border-gray-300 px-3 py-2 text-left w-2/3 font-bold">Terms & Conditions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Nature of Facility</td>
                                    <td className="border border-gray-300 px-3 py-2">Personal Loan</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Sanction Limit</td>
                                    <td className="border border-gray-300 px-3 py-2">Rs. {loanDetails.amount.toLocaleString('en-IN')}</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Purpose of Loan</td>
                                    <td className="border border-gray-300 px-3 py-2">Personal Requirements / Household Expenses</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Security</td>
                                    <td className="border border-gray-300 px-3 py-2">Unsecured (Clean)</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Margin</td>
                                    <td className="border border-gray-300 px-3 py-2">NIL</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Rate of Interest</td>
                                    <td className="border border-gray-300 px-3 py-2">
                                        Fixed Rate of <strong>{loanDetails.interest_rate}% p.a.</strong>
                                    </td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Penal Interest</td>
                                    <td className="border border-gray-300 px-3 py-2">
                                        2% per month on the overdue amount for the period of irregularity.
                                    </td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Processing Charges</td>
                                    <td className="border border-gray-300 px-3 py-2">
                                        2.50% of the loan amount + applicable GST
                                    </td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Repayment Period</td>
                                    <td className="border border-gray-300 px-3 py-2">
                                        {loanDetails.tenure_months} Months; Monthly Installments
                                    </td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-300 px-3 py-2 font-semibold">Monthly EMI</td>
                                    <td className="border border-gray-300 px-3 py-2 font-bold">
                                        Rs. {loanDetails.monthly_emi.toLocaleString('en-IN')}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    {/* Other Terms */}
                    <div className="mb-8">
                        <h4 className="font-bold mb-2">Other terms & conditions:</h4>
                        <ol className="list-[lower-alpha] space-y-2 pl-5 text-justify">
                            <li>The arrangement may be cancelled immediately on written notice to that effect given by the Bank to you without prejudice to any liability under the arrangement.</li>
                            <li>Undertaking to abide by the terms and conditions stipulated and/or may be stipulated from time to time for loan under TATA PERSONAL LOAN SCHEME.</li>
                            <li>The Bank will be free to verify the information submitted in your loan application form from any source about your employment, income, or any other aspect considered necessary by the bank.</li>
                            <li>Disbursement of the credit facilities will be made in your existing saving account registered with us.</li>
                            <li>The EMI will be debited via NACH/e-Mandate from your registered bank account on the 5th of every month.</li>
                        </ol>
                    </div>

                    {/* Footer - Signatures */}
                    <div className="mt-16 flex justify-between items-end avoid-break">
                        <div>
                            <p className="font-bold">Accepted by:</p>
                            <div className="mt-8 border-t border-gray-400 w-48 text-center pt-1 text-xs">
                                (Signature of Borrower)
                            </div>
                        </div>

                        <div className="text-right">
                            <p className="font-bold mb-8">For Tata Capital Financial Services Limited</p>
                            {/* Digital Signature Placeholder */}
                            <div className="inline-block relative">
                                <div className="absolute -top-12 right-0 w-32 h-32 opacity-20 border-2 border-blue-800 rounded-full flex items-center justify-center -rotate-12 pointer-events-none">
                                    <span className="text-xs font-bold text-blue-800 uppercase text-center">
                                        Tata Capital<br />Authorized<br />Signatory
                                    </span>
                                </div>
                                <p className="font-bold">Authorized Signatory</p>
                            </div>
                        </div>
                    </div>

                    {/* Footer Note */}
                    <div className="mt-12 text-center text-xs text-gray-500 border-t pt-4">
                        <p>Tata Capital Financial Services Limited | Registered Office: 11th Floor, Tower A, Peninsula Business Park, Ganpatrao Kadam Marg, Lower Parel, Mumbai - 400013</p>
                        <p>Corporate Identity Number: U67190MH2008PLC187552</p>
                    </div>

                </div>
            </div>

            {/* CSS for printing and PDF generation to handle color compatibility */}
            <style>{`
                @media print {
                    body * {
                        visibility: hidden;
                    }
                    .fixed, .fixed * {
                        visibility: visible;
                    }
                    .fixed {
                        position: absolute;
                        left: 0;
                        top: 0;
                        width: 100%;
                        height: auto;
                        min-height: 100%;
                        background: white !important;
                        z-index: 9999;
                    }
                    .print\\:shadow-none {
                        box-shadow: none !important;
                    }
                    .avoid-break {
                        break-inside: avoid;
                    }
                }

                /* Override Tailwind OKLCH colors with HEX for html2canvas compatibility */
                #sanction-letter-content {
                    background-color: #ffffff !important;
                    color: #1f2937 !important; /* gray-800 */
                }
                #sanction-letter-content .bg-white { background-color: #ffffff !important; }
                #sanction-letter-content .bg-gray-100 { background-color: #f3f4f6 !important; }
                #sanction-letter-content .text-gray-800 { color: #1f2937 !important; }
                #sanction-letter-content .text-gray-700 { color: #374151 !important; }
                #sanction-letter-content .text-gray-600 { color: #4b5563 !important; }
                #sanction-letter-content .text-gray-500 { color: #6b7280 !important; }
                #sanction-letter-content .text-blue-800 { color: #1e40af !important; }
                #sanction-letter-content .border-gray-300 { border-color: #d1d5db !important; }
                #sanction-letter-content .border-gray-400 { border-color: #9ca3af !important; }
                #sanction-letter-content .border-red-700 { border-color: #b91c1c !important; }
                #sanction-letter-content .border-blue-800 { border-color: #1e40af !important; }
            `}</style>
        </div>
    );
};

// Helper to convert number to words (Simplified version for efficiency)
function convertNumberToWords(amount: number): string {
    const units = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine'];
    const teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

    if (amount === 0) return 'Zero';

    // Simple implementation for demo purposes - handles up to Lakhs properly
    // For a production app, use a library like 'number-to-words'

    if (amount >= 100000) {
        const lakhs = Math.floor(amount / 100000);
        const remainder = amount % 100000;
        return `${convertNumberToWords(lakhs)} Lakh ${remainder > 0 ? convertNumberToWords(remainder) : ''}`;
    }

    if (amount >= 1000) {
        const thousands = Math.floor(amount / 1000);
        const remainder = amount % 1000;
        return `${convertNumberToWords(thousands)} Thousand ${remainder > 0 ? convertNumberToWords(remainder) : ''}`;
    }

    if (amount >= 100) {
        const hundreds = Math.floor(amount / 100);
        const remainder = amount % 100;
        return `${units[hundreds]} Hundred ${remainder > 0 ? convertNumberToWords(remainder) : ''}`;
    }

    if (amount >= 20) {
        const ten = Math.floor(amount / 10);
        const unit = amount % 10;
        return `${tens[ten]} ${units[unit]}`;
    }

    if (amount >= 10) {
        return teens[amount - 10];
    }

    return units[amount];
}
