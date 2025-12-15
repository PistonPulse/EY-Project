import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget } from '../components/ChatWidget';
import { Phone, Mail, MapPin, Clock, Send, MessageCircle } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import { useState } from 'react';

export function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: ''
  });

  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-[#004589] to-[#0066cc] text-white">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl mb-6">Contact Us</h1>
          <p className="text-xl opacity-90 max-w-2xl mx-auto">
            Have questions? We&apos;re here to help. Reach out to us through any of the channels below.
          </p>
        </div>
      </section>

      {/* Contact Info Cards */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-6 -mt-24 mb-16">
            <div className="bg-white rounded-xl shadow-xl p-6 text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Phone className="w-6 h-6 text-[#004589]" />
              </div>
              <h3 className="text-gray-900 mb-2">Call Us</h3>
              <p className="text-[#004589] mb-1">1800-209-8800</p>
              <p className="text-sm text-gray-600">Toll-free</p>
            </div>

            <div className="bg-white rounded-xl shadow-xl p-6 text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mail className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-gray-900 mb-2">Email Us</h3>
              <p className="text-[#004589] mb-1 text-sm">
                customersupport@tatacapital.com
              </p>
              <p className="text-sm text-gray-600">24/7 support</p>
            </div>

            <div className="bg-white rounded-xl shadow-xl p-6 text-center">
              <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageCircle className="w-6 h-6 text-amber-600" />
              </div>
              <h3 className="text-gray-900 mb-2">Live Chat</h3>
              <p className="text-[#004589] mb-1">AI Assistant</p>
              <p className="text-sm text-gray-600">Instant response</p>
            </div>

            <div className="bg-white rounded-xl shadow-xl p-6 text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Clock className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-gray-900 mb-2">Working Hours</h3>
              <p className="text-[#004589] mb-1">Mon-Sat</p>
              <p className="text-sm text-gray-600">9:00 AM - 6:00 PM</p>
            </div>
          </div>

          {/* Form & Map Section */}
          <div className="grid lg:grid-cols-2 gap-8">
            {/* Contact Form */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl text-gray-900 mb-6">Send Us a Message</h2>

              {submitted && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                  <p className="text-green-800">
                    Thank you! Your message has been sent successfully. We&apos;ll get back to you soon.
                  </p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-gray-700 mb-2">Full Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-[#004589]"
                    placeholder="Enter your name"
                  />
                </div>

                <div>
                  <label className="block text-gray-700 mb-2">Email Address *</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-[#004589]"
                    placeholder="your.email@example.com"
                  />
                </div>

                <div>
                  <label className="block text-gray-700 mb-2">Phone Number *</label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-[#004589]"
                    placeholder="+91 98765 43210"
                  />
                </div>

                <div>
                  <label className="block text-gray-700 mb-2">Subject *</label>
                  <select
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-[#004589]"
                  >
                    <option value="">Select a subject</option>
                    <option value="loan-enquiry">Loan Enquiry</option>
                    <option value="existing-customer">Existing Customer Support</option>
                    <option value="complaint">Complaint/Grievance</option>
                    <option value="feedback">Feedback</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-700 mb-2">Message *</label>
                  <textarea
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    rows={5}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-[#004589] resize-none"
                    placeholder="Tell us how we can help..."
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-[#004589] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors flex items-center justify-center gap-2"
                >
                  <Send className="w-5 h-5" />
                  Send Message
                </button>
              </form>
            </div>

            {/* Office Info & Image */}
            <div className="space-y-6">
              {/* Image */}
              <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                <ImageWithFallback
                  src="https://images.unsplash.com/photo-1556740749-887f6717d7e4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjdXN0b21lciUyMHNlcnZpY2UlMjBwcm9mZXNzaW9uYWx8ZW58MXx8fHwxNzY1MTAyNDU2fDA&ixlib=rb-4.1.0&q=80&w=1080"
                  alt="Customer service"
                  className="w-full h-64 object-cover"
                />
              </div>

              {/* Head Office */}
              <div className="bg-white rounded-xl shadow-lg p-8">
                <h3 className="text-xl text-gray-900 mb-4">Head Office</h3>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <MapPin className="w-5 h-5 text-[#004589] flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-gray-700">
                        Tata Capital Limited
                        <br />
                        11th Floor, Tower A,
                        <br />
                        Peninsula Business Park,
                        <br />
                        Ganpatrao Kadam Marg,
                        <br />
                        Lower Parel, Mumbai - 400013
                        <br />
                        Maharashtra, India
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Phone className="w-5 h-5 text-[#004589] flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-gray-700">+91 22 6778 9000</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Mail className="w-5 h-5 text-[#004589] flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-gray-700">info@tatacapital.com</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Branch Locator */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
                <h3 className="text-xl text-gray-900 mb-3">Find a Branch Near You</h3>
                <p className="text-gray-700 mb-4">
                  We have 600+ branches across India. Find your nearest Tata Capital branch.
                </p>
                <button className="w-full bg-[#004589] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors">
                  Branch Locator
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Regional Offices */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Regional Offices</h2>
            <p className="text-xl text-gray-600">Connect with us across major cities in India</p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { city: 'Delhi NCR', address: 'Connaught Place, New Delhi' },
              { city: 'Bangalore', address: 'MG Road, Bangalore' },
              { city: 'Chennai', address: 'Anna Salai, Chennai' },
              { city: 'Kolkata', address: 'Park Street, Kolkata' },
              { city: 'Hyderabad', address: 'Banjara Hills, Hyderabad' },
              { city: 'Pune', address: 'Koregaon Park, Pune' },
              { city: 'Ahmedabad', address: 'CG Road, Ahmedabad' },
              { city: 'Jaipur', address: 'MI Road, Jaipur' }
            ].map((office, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-gray-900 mb-2">{office.city}</h4>
                <p className="text-sm text-gray-600">{office.address}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ CTA */}
      <section className="py-16 px-6 bg-gradient-to-r from-[#004589] to-[#3B82F6] text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Looking for Quick Answers?</h2>
          <p className="text-xl mb-8 opacity-90">
            Check out our FAQ section for instant answers to common questions
          </p>
          <button className="bg-white text-[#004589] px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
            View FAQs
          </button>
        </div>
      </section>

      <Footer />
      <ChatWidget />
    </div>
  );
}