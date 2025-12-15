import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget } from '../components/ChatWidget';
import { ChevronDown, Search, HelpCircle } from 'lucide-react';
import { useState } from 'react';

export function FAQs() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');

  const categories = [
    { id: 'all', name: 'All FAQs' },
    { id: 'personal-loans', name: 'Personal Loans' },
    { id: 'home-loans', name: 'Home Loans' },
    { id: 'business-loans', name: 'Business Loans' },
    { id: 'application', name: 'Application Process' },
    { id: 'repayment', name: 'Repayment' }
  ];

  const faqs = [
    {
      category: 'personal-loans',
      question: 'What is the minimum and maximum loan amount for personal loans?',
      answer:
        'You can apply for personal loans ranging from ₹50,000 to ₹25 lakhs, depending on your eligibility, income, and credit profile.'
    },
    {
      category: 'personal-loans',
      question: 'What is the interest rate for personal loans?',
      answer:
        'Interest rates for personal loans start from 10.5% p.a. and vary based on your credit score, income level, employment type, and loan amount. Prime customers with excellent credit scores get the best rates.'
    },
    {
      category: 'personal-loans',
      question: 'What is the loan tenure for personal loans?',
      answer:
        'Personal loan tenures range from 12 months to 60 months (1 to 5 years). You can choose a tenure that best suits your repayment capacity.'
    },
    {
      category: 'home-loans',
      question: 'What documents are required for a home loan?',
      answer:
        'Basic documents include: Identity proof (Aadhaar/PAN), Address proof, Income proof (salary slips/ITR), Bank statements for 6 months, Property documents, and photographs. All documents can be submitted digitally.'
    },
    {
      category: 'home-loans',
      question: 'What is the maximum home loan amount I can get?',
      answer:
        'Home loans are available up to ₹10 crores. The exact amount depends on your income, credit history, property value, and loan-to-value ratio. Typically, you can get up to 80-90% of the property value.'
    },
    {
      category: 'home-loans',
      question: 'Can I get tax benefits on home loans?',
      answer:
        'Yes! You can claim deductions under Section 80C for principal repayment (up to ₹1.5 lakhs) and Section 24 for interest payment (up to ₹2 lakhs). First-time homebuyers get additional benefits under Section 80EEA.'
    },
    {
      category: 'business-loans',
      question: 'Who is eligible for a business loan?',
      answer:
        'Business loans are available for self-employed individuals, proprietors, partnerships, and companies. Your business should be operational for at least 2 years with a minimum annual turnover of ₹10 lakhs.'
    },
    {
      category: 'business-loans',
      question: 'Is collateral required for business loans?',
      answer:
        'For loans up to ₹10 lakhs, no collateral is required. For higher amounts, we may require collateral depending on your business profile and creditworthiness.'
    },
    {
      category: 'application',
      question: 'How long does it take to get loan approval?',
      answer:
        'With our AI-powered system, personal loan approvals happen within 5 minutes! For other loan types, approval typically takes 24-48 hours once all documents are verified.'
    },
    {
      category: 'application',
      question: 'What is the minimum credit score required?',
      answer:
        'We typically require a CIBIL score of 650 or above. However, if you have a strong income profile and stable employment, we may consider applications with slightly lower scores.'
    },
    {
      category: 'application',
      question: 'Can I apply for a loan online?',
      answer:
        'Yes! You can apply for all our loan products online through our website or mobile app. Our AI assistant will guide you through the entire process. The process is 100% digital and paperless.'
    },
    {
      category: 'application',
      question: 'What is the age criteria for applying for a loan?',
      answer:
        'You must be between 21 and 65 years old for salaried individuals. For self-employed individuals, the maximum age is 70 years. Some loan products may have different age criteria.'
    },
    {
      category: 'repayment',
      question: 'How do I repay my loan?',
      answer:
        'You can repay through multiple convenient methods: Auto-debit from your bank account (recommended), Online payment through our website/app, NACH mandate, Cheque/DD, or UPI. EMI is deducted on a fixed date each month.'
    },
    {
      category: 'repayment',
      question: 'Can I prepay my loan? Are there any charges?',
      answer:
        'Yes, you can prepay your loan partially or fully at any time. For personal loans, there are no prepayment charges. For other loan types, minimal charges may apply (typically 2-4% of the outstanding amount).'
    },
    {
      category: 'repayment',
      question: 'What happens if I miss an EMI payment?',
      answer:
        'Missing an EMI can result in late payment charges and negatively impact your credit score. We recommend setting up auto-debit to avoid missing payments. If you face financial difficulties, contact us immediately to discuss restructuring options.'
    },
    {
      category: 'repayment',
      question: 'Can I change my EMI date?',
      answer:
        'Yes, you can request to change your EMI date once during the loan tenure. Contact our customer support team with your preferred date, and we\'ll process the request within 7 working days.'
    }
  ];

  const filteredFaqs = faqs.filter((faq) => {
    const matchesCategory = activeCategory === 'all' || faq.category === activeCategory;
    const matchesSearch =
      searchQuery === '' ||
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-[#004589] to-[#0066cc] text-white">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block bg-white/10 backdrop-blur-sm rounded-full p-4 mb-6">
            <HelpCircle className="w-12 h-12" />
          </div>
          <h1 className="text-5xl mb-6">Frequently Asked Questions</h1>
          <p className="text-xl opacity-90 mb-8">
            Find answers to common questions about our loan products and services
          </p>

          {/* Search Bar */}
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for answers..."
              className="w-full pl-12 pr-4 py-4 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>
        </div>
      </section>

      {/* Category Filter */}
      <section className="py-8 px-6 bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap gap-3 justify-center">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                className={`px-6 py-2 rounded-full transition-colors ${
                  activeCategory === category.id
                    ? 'bg-[#004589] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* FAQs List */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          {filteredFaqs.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-block bg-gray-100 rounded-full p-6 mb-4">
                <Search className="w-12 h-12 text-gray-400" />
              </div>
              <h3 className="text-xl text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-600">
                Try adjusting your search or filter to find what you&apos;re looking for
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredFaqs.map((faq, index) => (
                <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200">
                  <button
                    onClick={() => setOpenIndex(openIndex === index ? null : index)}
                    className="w-full flex items-center justify-between p-6 text-left hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-gray-900 pr-8">{faq.question}</span>
                    <ChevronDown
                      className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform ${
                        openIndex === index ? 'transform rotate-180' : ''
                      }`}
                    />
                  </button>
                  {openIndex === index && (
                    <div className="px-6 pb-6">
                      <p className="text-gray-700 leading-relaxed">{faq.answer}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Still Need Help Section */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-8 border border-blue-100">
            <div className="text-center">
              <h2 className="text-2xl text-gray-900 mb-4">Still Need Help?</h2>
              <p className="text-gray-700 mb-6">
                Can&apos;t find the answer you&apos;re looking for? Our support team is here to help.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button className="bg-[#004589] text-white px-8 py-3 rounded-lg hover:bg-[#003366] transition-colors">
                  Chat with AI Assistant
                </button>
                <button className="border-2 border-[#004589] text-[#004589] px-8 py-3 rounded-lg hover:bg-[#004589] hover:text-white transition-colors">
                  Contact Support
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Popular Topics */}
      <section className="py-16 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Popular Topics</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <h3 className="text-xl text-gray-900 mb-3">Loan Eligibility</h3>
              <p className="text-gray-600 mb-4">
                Learn about eligibility criteria, documents required, and how to improve your
                chances of approval.
              </p>
              <button className="text-[#004589] hover:underline">Learn more →</button>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <h3 className="text-xl text-gray-900 mb-3">Interest Rates</h3>
              <p className="text-gray-600 mb-4">
                Understand how interest rates are calculated and what factors affect your loan
                interest rate.
              </p>
              <button className="text-[#004589] hover:underline">Learn more →</button>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <h3 className="text-xl text-gray-900 mb-3">Repayment Options</h3>
              <p className="text-gray-600 mb-4">
                Explore different repayment methods, EMI structures, and prepayment options
                available.
              </p>
              <button className="text-[#004589] hover:underline">Learn more →</button>
            </div>
          </div>
        </div>
      </section>

      <Footer />
      <ChatWidget />
    </div>
  );
}